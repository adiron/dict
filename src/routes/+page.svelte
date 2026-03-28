<script lang="ts">
  import type { PageData } from './$types';
  import Entry from '$lib/components/Entry.svelte';

  let { data }: { data: PageData } = $props();

  let openId = $state<number | null>(null);
  let inputEl: HTMLInputElement;
  let searchBarEl: HTMLFormElement;

  const OVERSHOOT = 10; // extra px past -height to ensure no peeking

  let searchOffset = 0;  // shared between scroll handler and snap
  let snapping = false;

  $effect(() => {
    let lastY = window.scrollY;

    function onScroll() {
      const y = window.scrollY;
      const delta = y - lastY;
      lastY = y; // always keep lastY current, even while snapping
      if (snapping) return;
      const min = -(searchBarEl?.offsetHeight ?? 0) - OVERSHOOT;
      searchOffset = delta > 0
        ? Math.max(searchOffset - delta, min)
        : Math.min(searchOffset - delta, 0);

      if (searchBarEl) searchBarEl.style.transform = `translateY(${searchOffset}px)`;
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  });

  function snapSearchIntoView() {
    if (!searchBarEl || searchOffset === 0) return;
    snapping = true;
    searchBarEl.style.transition = 'transform 0.25s ease';
    searchBarEl.style.transform = 'translateY(0)';
    searchBarEl.addEventListener('transitionend', () => {
      searchOffset = 0;
      snapping = false;
      if (searchBarEl) searchBarEl.style.transition = '';
    }, { once: true });
  }

  $effect(() => {
    // On navigation, open the linked entry if specified, else default to first
    openId = data.openId ?? data.results?.entries[0]?.id ?? null;
  });

  $effect(() => {
    const empty = !data.results ||
      (data.results.entries.length === 0 && data.results.phrases.length === 0);
    if (!data.q || empty) inputEl?.focus();
  });
</script>

<svelte:head>
  <title>{data.q ? `${data.q} - Dict` : 'Dict'}</title>
</svelte:head>

<main>
  <form class="search-bar" bind:this={searchBarEl} method="GET" action="/" onfocusin={snapSearchIntoView}>
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
          <Entry
            {entry}
            open={openId === entry.id}
            scroll={i !== 0}
            scrollOffset={() => {
              if (!searchBarEl) return 0;
              const transform = new DOMMatrix(getComputedStyle(searchBarEl).transform);
              const visibleHeight = searchBarEl.offsetHeight + transform.m42; // m42 = translateY
              return Math.max(visibleHeight, 0);
            }}
            onopen={() => { openId = entry.id; }}
          />
        {/each}

        {#if data.results.phrases.length > 0}
          <section class="phrases-section">
            <h2>Phrases</h2>
            <ul>
              {#each data.results.phrases as phrase (phrase.id)}
                <li>
                  <strong>{phrase.dutch}</strong> - {phrase.translation}
                  <a class="ref" href="/?q={encodeURIComponent(phrase.headword)}">({phrase.headword})</a>
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
    position: sticky;
    top: var(--padding);
    z-index: 10;
    will-change: transform;
    display: flex;
    align-items: center;
    gap: 1rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--bg);
    padding: 8px 1rem;
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
