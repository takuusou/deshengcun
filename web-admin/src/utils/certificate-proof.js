function normalizeText(value, fallback = "") {
  const text = String(value ?? "").trim();
  return text || fallback;
}

function buildRelationText(value) {
  const text = normalizeText(value, "________");
  return text.endsWith("关系") ? text : `${text}关系`;
}

function buildParagraphText(value) {
  return `　　${String(value || "").trim()}`;
}

function buildDocumentTitle(application) {
  return (
    normalizeText(application?.extra_fields?.certificate_title) ||
    normalizeText(application?.selected_option).replace(/^开具证明[:：]\s*/, "") ||
    "村级文书"
  );
}

function getCertificateKey(application) {
  return normalizeText(application?.extra_fields?.certificate_key);
}

function isConsentDocument(application) {
  const title = buildDocumentTitle(application);
  const certificateKey = getCertificateKey(application);
  return certificateKey === "charger_install" || title.includes("同意书");
}

function buildCertificateSubject(application) {
  return buildDocumentTitle(application);
}

function formatIdentitySentence(name, gender, idCard, suffix = "") {
  return `${normalizeText(name, "________")}，${normalizeText(gender, "________")}，公民身份号码${normalizeText(idCard, "________")}${suffix}`;
}

function buildCertificateParagraphs(application) {
  const fields = application?.extra_fields || {};
  const applicantName = normalizeText(fields.name || application?.applicant_name, "________");
  const applicantGender = normalizeText(fields.gender, "________");
  const applicantIdCard = normalizeText(fields.id_card, "________");
  const relationName = normalizeText(fields.related_name, "");
  const relationIdCard = normalizeText(fields.related_id_card, "");
  const isRelationship = !!relationName || !!relationIdCard || !!normalizeText(fields.relation_type);
  const documentTitle = buildDocumentTitle(application);
  const reasonText = normalizeText(fields.job_desc, "");

  if (isRelationship) {
    return [
      buildParagraphText(`兹证明：${formatIdentitySentence(applicantName, applicantGender, applicantIdCard, "，系我村村民。")}`),
      buildParagraphText(
        `经核实：${formatIdentitySentence(
          normalizeText(relationName, "________"),
          normalizeText(fields.related_gender, "________"),
          normalizeText(relationIdCard, "________"),
          `，与${applicantName}系${buildRelationText(fields.relation_type)}。`
        )}`
      ),
      buildParagraphText("上述情况属实，特此证明。"),
    ];
  }

  if (isConsentDocument(application)) {
    const actionText = documentTitle.replace(/同意书$/, "").trim() || "相关事项";
    return [
      buildParagraphText(`兹有我村村民${applicantName}，${applicantGender}，公民身份号码${applicantIdCard}。`),
      buildParagraphText(
        reasonText
          ? `现因${reasonText}，申请办理${actionText}相关手续。`
          : `现申请办理${actionText}相关手续。`
      ),
      buildParagraphText(`经核实，该申请人身份及申请事项属实，我村对其按规定办理${actionText}相关手续无异议。`),
      buildParagraphText("特此同意。"),
    ];
  }

  return [
    buildParagraphText(`兹证明：${formatIdentitySentence(applicantName, applicantGender, applicantIdCard, "，系我村村民。")}`),
    buildParagraphText(
      reasonText
        ? `因${reasonText}需要，现申请出具${documentTitle}。`
        : `现申请出具${documentTitle}。`
    ),
    buildParagraphText("上述情况属实，特此证明。"),
  ];
}

function wrapLine(ctx, text, maxWidth) {
  const source = String(text || "");
  if (!source.trim()) {
    return [];
  }
  const lines = [];
  let current = "";
  const tokens = source.match(/\d+|[A-Za-z]+|./gu) || [];
  for (const token of tokens) {
    const candidate = `${current}${token}`;
    if (!current || ctx.measureText(candidate).width <= maxWidth) {
      current = candidate;
      continue;
    }
    lines.push(current);
    current = token;
  }
  if (current) {
    lines.push(current);
  }
  return lines;
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.crossOrigin = "anonymous";
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("电子章图片加载失败，请刷新后台后重试。"));
    image.src = src;
  });
}

function canvasToBlob(canvas) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error("电子证明生成失败，请稍后重试。"));
        return;
      }
      resolve(blob);
    }, "image/png");
  });
}

function buildSealCanvas(image) {
  const canvas = document.createElement("canvas");
  canvas.width = image.width;
  canvas.height = image.height;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return image;
  }
  ctx.drawImage(image, 0, 0);
  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const { data } = imageData;
  for (let index = 0; index < data.length; index += 4) {
    const red = data[index];
    const green = data[index + 1];
    const blue = data[index + 2];
    if (red > 236 && green > 236 && blue > 236) {
      data[index + 3] = 0;
    }
  }
  ctx.putImageData(imageData, 0, 0);
  return canvas;
}

function formatChineseDate(value = new Date()) {
  return `${value.getFullYear()}年${value.getMonth() + 1}月${value.getDate()}日`;
}

function resolveTitleFontSize(ctx, title, maxWidth) {
  let fontSize = 64;
  while (fontSize > 42) {
    ctx.font = `700 ${fontSize}px "PingFang SC", "Microsoft YaHei", sans-serif`;
    if (ctx.measureText(title).width <= maxWidth) {
      break;
    }
    fontSize -= 2;
  }
  return fontSize;
}

export async function buildStampedCertificateFile(application, sealImageUrl) {
  const canvas = document.createElement("canvas");
  canvas.width = 1240;
  canvas.height = 1754;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("当前浏览器不支持电子证明生成。");
  }

  ctx.fillStyle = "#fffdf7";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = "#e8dcc1";
  ctx.lineWidth = 4;
  ctx.strokeRect(36, 36, canvas.width - 72, canvas.height - 72);
  ctx.strokeStyle = "rgba(206, 183, 145, 0.52)";
  ctx.lineWidth = 2;
  ctx.strokeRect(60, 60, canvas.width - 120, canvas.height - 120);

  ctx.fillStyle = "#1f2937";
  ctx.textBaseline = "top";

  const left = 132;
  const right = canvas.width - 132;
  const contentWidth = right - left;
  let cursorY = 160;

  const documentTitle = buildDocumentTitle(application);
  const titleFontSize = resolveTitleFontSize(ctx, documentTitle, contentWidth);
  ctx.font = `700 ${titleFontSize}px "PingFang SC", "Microsoft YaHei", sans-serif`;
  ctx.textAlign = "center";
  ctx.fillText(documentTitle, canvas.width / 2, cursorY);
  cursorY += titleFontSize >= 58 ? 86 : 78;

  ctx.strokeStyle = "rgba(206, 183, 145, 0.7)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(canvas.width / 2 - 160, cursorY);
  ctx.lineTo(canvas.width / 2 + 160, cursorY);
  ctx.stroke();
  cursorY += 72;

  ctx.fillStyle = "#1f2937";
  ctx.font = '500 34px "PingFang SC", "Microsoft YaHei", sans-serif';
  ctx.textAlign = "left";
  for (const paragraph of buildCertificateParagraphs(application)) {
    const lines = wrapLine(ctx, paragraph, contentWidth);
    lines.forEach((line) => {
      ctx.fillText(line, left, cursorY);
      cursorY += 56;
    });
    cursorY += 26;
  }

  const signText = "上塔市镇得胜村村民委员会";
  const issueDate = formatChineseDate(new Date());
  cursorY = Math.max(cursorY + 210, canvas.height - 405);

  ctx.font = '600 40px "PingFang SC", "Microsoft YaHei", sans-serif';
  const signWidth = ctx.measureText(signText).width;
  const signX = right - signWidth;
  ctx.fillText(signText, signX, cursorY);

  cursorY += 78;
  ctx.font = '500 34px "PingFang SC", "Microsoft YaHei", sans-serif';
  const dateText = issueDate;
  const dateWidth = ctx.measureText(dateText).width;
  ctx.fillText(dateText, right - dateWidth, cursorY);

  const sealImage = buildSealCanvas(await loadImage(sealImageUrl));
  const sealSize = 250;
  const sealX = right - sealSize - 30;
  const sealY = cursorY - 78;
  ctx.save();
  ctx.globalAlpha = 0.5;
  ctx.drawImage(sealImage, sealX, sealY, sealSize, sealSize);
  ctx.restore();

  const blob = await canvasToBlob(canvas);
  return new File([blob], `certificate-${Number(application?.id || 0) || "result"}.png`, {
    type: "image/png",
  });
}
