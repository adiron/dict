<script lang="ts">
  import type { SearchResponse } from '../server/types.ts';

  let query = $state('');
  let results = $state<SearchResponse | null>(null);
  let loading = $state(false);
  let error = $state<string | null>(null);

  async function handleSubmit(e: SubmitEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    loading = true;
    error = null;

    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(query.trim())}`);
      if (!res.ok) throw new Error(`${res.status}`);
      results = await res.json() as SearchResponse;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Something went wrong';
    } finally {
      loading = false;
    }
  }
</script>

<main>
  <form onsubmit={handleSubmit}>
    <input
      type="search"
      bind:value={query}
      placeholder="Search Dutch..."
      autofocus
    />
    <button type="submit" disabled={loading}>Search</button>
  </form>

  {#if error}
    <p class="error">{error}</p>
  {/if}

  {#if results}
    {#if results.entries.length > 0}
      <section>
        <h2>Entries</h2>
        <ul>
          {#each results.entries as entry (entry.id)}
            <li>
              {#if entry.matched_inflection}
                <span class="inflection-match"><em>{entry.matched_inflection}</em> → </span>
              {/if}
              <strong>{entry.headword}</strong>
              {#if entry.homonym_num}<sup>{entry.homonym_num}</sup>{/if}
              {#if entry.pos}<span class="pos">{entry.pos}</span>{/if}
              {#if entry.article}<span class="article">{entry.article}</span>{/if}
            </li>
          {/each}
        </ul>
      </section>
    {/if}

    {#if results.phrases.length > 0}
      <section>
        <h2>Phrases</h2>
        <ul>
          {#each results.phrases as phrase (phrase.id)}
            <li>
              <strong>{phrase.dutch}</strong> - {phrase.translation}
              <span class="headword-ref">({phrase.headword})</span>
            </li>
          {/each}
        </ul>
      </section>
    {/if}

    {#if results.entries.length === 0 && results.phrases.length === 0}
      <p>No results for <em>{query}</em>.</p>
    {/if}
  {/if}
</main>

<style>
  .pos { color: #888; font-size: 0.85em; margin-left: 0.4em; }
  .article { color: #aaa; font-size: 0.85em; margin-left: 0.4em; }
  .headword-ref { color: #aaa; font-size: 0.85em; }
  .inflection-match { color: #aaa; font-size: 0.9em; }
  .error { color: red; }
</style>
