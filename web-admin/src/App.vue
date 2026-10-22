<template>
  <Transition name="success-toast">
    <div v-if="successToast" class="global-success-toast" role="status">
      <span class="global-success-toast-dot"></span>
      <span>{{ successToast }}</span>
    </div>
  </Transition>
  <RouterView />
</template>

<script setup>
import { RouterView } from "vue-router";
import { useSuccessToastState } from "./utils/success-toast";

const successToast = useSuccessToastState();
</script>
