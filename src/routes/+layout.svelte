<script lang="ts">
  import '../app.scss';
  import { navigating } from '$app/stores';
  let { children } = $props();
</script>

{#if $navigating}
  <div class="page-loader" aria-hidden="true"></div>
{/if}

{@render children()}

<style>
  .page-loader {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    z-index: 1000;
    background: linear-gradient(
      90deg,
      transparent 0%,
      var(--fg) 40%,
      var(--fg) 60%,
      transparent 100%
    );
    background-size: 40% 100%;
    animation: loader-sweep 0.9s ease-in-out infinite;
  }

  @keyframes loader-sweep {
    from { background-position: -50% 0; }
    to   { background-position: 150% 0; }
  }
</style>
