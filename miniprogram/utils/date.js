function pad2(value) {
  return String(value).padStart(2, "0");
}

function formatDateCore(value, withTime = false) {
  const text = String(value || "").trim();
  if (!text) {
    return "";
  }

  const date = new Date(text);
  if (Number.isNaN(date.getTime())) {
    return withTime ? text.slice(0, 16).replace("T", " ") : text.slice(0, 10);
  }

  const dateText = `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
  if (!withTime) {
    return dateText;
  }
  return `${dateText} ${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

function formatLocalDate(value) {
  return formatDateCore(value, false);
}

function formatLocalDateTime(value) {
  return formatDateCore(value, true);
}

module.exports = {
  formatLocalDate,
  formatLocalDateTime,
};
