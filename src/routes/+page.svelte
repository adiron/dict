<script lang="ts">
  import type { PageData } from './$types';
  import Entry from '$lib/components/Entry.svelte';

  let { data }: { data: PageData } = $props();

  let openId = $state<number | null>(null);
  let inputEl: HTMLInputElement;

  $effect(() => {
    // Reset to first entry whenever results change
    openId = data.results?.entries[0]?.id ?? null;
  });

  $effect(() => {
    const empty = !data.results ||
      (data.results.entries.length === 0 && data.results.phrases.length === 0);
    if (!data.q || empty) inputEl?.focus();
  });
</script>

<main>
  <form class="search-bar" method="GET" action="/">
    <input
      class="search-input"
      type="search"
      name="q"
      value={data.q}
      placeholder="Search dictionary..."
      autocomplete="off"
      spellcheck="false"
      bind:this={inputEl}
    />
    {#if data.q}
      <a class="search-action" href="/">clear</a>
    {/if}
    <button class="search-action" type="submit">search</button>
  </form>

  {#if data.results}
    {#if data.results.entries.length > 0 || data.results.phrases.length > 0}
      <div class="results">
        {#each data.results.entries as entry, i (entry.id)}
          <Entry {entry} open={openId === entry.id} scroll={i !== 0} onopen={() => { openId = entry.id; }} />
        {/each}

        {#if data.results.phrases.length > 0}
          <section class="phrases-section">
            <h2>Phrases</h2>
            <ul>
              {#each data.results.phrases as phrase (phrase.id)}
                <li>
                  <strong>{phrase.dutch}</strong> - {phrase.translation}
                  <a class="ref" href="/entry/{phrase.entry_id}">({phrase.headword})</a>
                </li>
              {/each}
            </ul>
          </section>
        {/if}
      </div>
    {:else}
      <p class="no-results">No results for <em>{data.q}</em>.</p>
    {/if}
  {/if}
</main>

<style lang="scss">
  .search-bar {
    display: flex;
    align-items: center;
    gap: 1rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--bg);
    padding: 8px 1rem;
    margin-bottom: 0;
  }

  .search-input {
    flex: 1;
    border: none;
    background: transparent;
    color: var(--fg);
    font-size: var(--textmd);
    font-family: inherit;
    outline: none;
    appearance: none;
    min-width: 0;

    &::placeholder { color: var(--textlight); }
    &::-webkit-search-cancel-button { display: none; }
  }

  .search-action {
    flex-shrink: 0;
    border: none;
    background: transparent;
    color: var(--textlight);
    font-size: var(--textmd);
    font-family: inherit;
    cursor: pointer;
    padding: 0;
    text-decoration: underline;
    white-space: nowrap;

    &:hover { color: var(--fg); }
  }

  .no-results {
    color: var(--textlight);
    font-size: var(--text-sm);
    margin-top: 1.5rem;
  }

  .phrases-section {
    padding: var(--itempadding) var(--padding);
    border-bottom: 1px solid var(--border);

    h2 {
      font-size: var(--text-xs);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--textlight);
      margin: 0 0 0.75rem;
    }

    ul { list-style: none; padding: 0; margin: 0; }
    li { font-size: var(--textmd); }
    li + li { margin-top: 0.4rem; }
  }

  .ref {
    color: var(--textlight);
    font-size: var(--text-sm);
  }
</style>
