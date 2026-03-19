<script lang="ts">
  import type { PageData } from './$types';
  import Entry from '$lib/components/Entry.svelte';

  let { data }: { data: PageData } = $props();
  const entry = $derived(data.entry);
</script>

<main>
  <nav><a href="/">← Search</a></nav>
  <Entry {entry} open />
</main>

<style>
  nav { margin-bottom: 1.5rem; }
</style>
