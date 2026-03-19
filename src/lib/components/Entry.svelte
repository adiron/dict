<script lang="ts">
  import type { Entry } from '$lib/types.js';
  import { posLabel } from '$lib/pos.js';

  let {
    entry,
    open = false,
    scroll = true,
    scrollOffset = () => 0,
    onopen,
  }: {
    entry: Entry;
    open?: boolean;
    scroll?: boolean;
    scrollOffset?: () => number;
    onopen?: () => void;
  } = $props();

  let el: HTMLDivElement;

  $effect(() => {
    // On mount: if already open (default first entry), skip transitions for first paint
    if (open) el?.classList.add('no-transition');
    requestAnimationFrame(() => {
      el?.classList.remove('no-transition');
    });
  });

  $effect(() => {
    if (!open || !scroll) return;

    const drawer = el?.querySelector<HTMLElement>(':scope > .drawer');
    if (!drawer) return;

    let fired = false;

    function check() {
      if (fired) return;
      fired = true;
      const rect = el.getBoundingClientRect();
      const padding = parseFloat(getComputedStyle(el).paddingTop);
      const offset = scrollOffset();
      const effectiveTop = rect.top - offset;
      if (effectiveTop < -padding || rect.bottom > window.innerHeight + padding) {
        const target = window.scrollY + rect.top - offset - padding;
        window.scrollTo({ top: target, behavior: 'smooth' });
      }
    }

    function onTransitionEnd(e: TransitionEvent) {
      if (e.propertyName === 'grid-template-rows') check();
    }

    drawer.addEventListener('transitionend', onTransitionEnd);
    const fallback = setTimeout(check, 500);

    return () => {
      drawer.removeEventListener('transitionend', onTransitionEnd);
      clearTimeout(fallback);
    };
  });
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<div class="entry" class:open role={open ? undefined : 'button'} bind:this={el} onclick={() => { if (!open) onopen?.(); }}>
  <div class="header-row">
    <div class="row-left">
      <div class="headword-group">
        {#if entry.matched_inflection}
          <span class="redirect">{entry.matched_inflection} →</span>
        {/if}
        {#if entry.article}
          <span class="article" class:het={entry.article === 'het'} class:de={entry.article === 'de'}>{entry.article}</span>
        {/if}
        <span class="headword">{entry.headword}{#if entry.homonym_num}<sup>{entry.homonym_num}</sup>{/if}</span>
      </div>
      {#if entry.pos}
        <span class="pos" title={posLabel(entry.pos)}>{entry.pos}</span>
      {/if}
    </div>
    <span class="more" aria-hidden="true">more</span>
  </div>

  <div class="drawer">
    <div class="drawer-inner">
      {#if entry.inflections.length > 0}
        <p class="inflections">Inflections: {entry.inflections.join(', ')}</p>
      {/if}

      <div class="body">{@html entry.body_html}</div>

      {#if entry.phrases.length > 0}
        <section class="phrases">
          <h2>Fixed expressions</h2>
          <ul>
            {#each entry.phrases as phrase (phrase.id)}
              <li>{@html phrase.body_html}</li>
            {/each}
          </ul>
        </section>
      {/if}
    </div>
  </div>
</div>

<style lang="scss">
  .entry {
    padding: var(--itempadding) var(--padding);
    border-bottom: 1px solid var(--border);
    transition: background-color 0.15s ease;

    &:global(.no-transition),
    &:global(.no-transition) * {
      transition: none !important;
    }

    &:not(.open) {
      cursor: pointer;

      &:hover {
        background-color: var(--hover);

        .more { opacity: 1; }
      }
    }

    // ── Header row ────────────────────────────────────────────────────────

    .header-row {
      display: flex;
      align-items: baseline;
      gap: 8px;
    }

    .row-left {
      display: flex;
      flex: 1;
      align-items: baseline;
      flex-wrap: wrap;
      gap: 8px;
      min-width: 0;
    }

    .headword-group {
      display: flex;
      align-items: baseline;
      flex-wrap: wrap;
      gap: 4px;
      font-size: var(--textmd);
      font-weight: 500;
      min-width: 0;
      transition: font-size 0.3s ease, gap 0.3s ease;
    }

    .redirect { color: var(--textlight); }

    .article {
      &.het { color: var(--het); }
      &.de  { color: var(--de); }
    }

    .headword {
      color: var(--fg);
      hyphens: auto;
      transition: font-weight 0.1s ease;
    }

    .pos {
      color: var(--textlight);
      font-size: var(--textmd);
      text-decoration: underline dotted;
      text-underline-offset: 3px;
      white-space: nowrap;
      flex-shrink: 0;
    }

    .more {
      flex-shrink: 0;
      margin-left: auto;
      color: var(--textlight);
      font-size: var(--textmd);
      text-decoration: underline;
      opacity: 0;
      transition: opacity 0.15s ease;
    }

    // ── Open state - header grows ─────────────────────────────────────────

    &.open {
      .headword-group {
        font-size: var(--textxl);
        gap: 6px;
      }

      .headword { font-weight: 700; }

      .more { display: none; }
    }

    // ── Drawer (animated height) ──────────────────────────────────────────

    .drawer {
      display: grid;
      grid-template-rows: 0fr;
      transition: grid-template-rows 0.35s cubic-bezier(0.4, 0, 0.2, 1);
    }

    &.open .drawer {
      grid-template-rows: 1fr;
    }

    .drawer-inner {
      overflow: hidden;
      display: flex;
      flex-direction: column;
      gap: 1rem;
      padding-top: 0;
      opacity: 0;
      transition:
        padding-top 0.35s ease,
        opacity 0.25s ease 0.1s;
    }

    &.open .drawer-inner {
      padding-top: 1rem;
      opacity: 1;
    }

    // ── Expanded content ──────────────────────────────────────────────────

    .inflections {
      color: var(--textlight);
      font-size: var(--text-sm);
      margin: 0;
    }

    // ── Body HTML skinning ────────────────────────────────────────────────

    .body {
      font-size: var(--textmd);
      color: var(--fg);
      width: 100%;

      // The body HTML from the dictionary uses: divs for structure,
      // b for bold translations and numbered items,
      // i for italic annotations and context hints,
      // blockquote for indented example phrases.
      :global {
        b { font-weight: 700; }

        i { color: var(--textlight); }

        blockquote {
          margin: 0.25rem 0 0;
          padding-left: 2em;
        }

        div + div { margin-top: 0.5em; }
      }
    }

    // ── Phrases ───────────────────────────────────────────────────────────

    .phrases {
      h2 {
        font-size: var(--text-xs);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--textlight);
        margin: 0 0 0.5rem;
      }

      ul {
        list-style: none;
        padding: 0;
        margin: 0;
        font-size: var(--textmd);
      }

      li + li { margin-top: 0.4rem; }
    }
  }
</style>
