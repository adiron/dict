/**
 * Maps Van Dale part-of-speech abbreviations to unabbreviated English labels.
 * Keys are the raw `pos` values stored in the database.
 */
export const POS_LABELS: Record<string, string> = {
  "zelfst nw": "zelfstandig naamwoord",
  "bn": "bijvoeglijk naamwoord",
  "bn, bw": "bijvoeglijk naamwoord / bijwoord",
  "bw": "bijwoord",
  "ov ww": "overgankelijk werkwoord",
  "onov ww": "onovergankelijk werkwoord",
  "ov ww, ook abs": "overgankelijk werkwoord",
  "onov ww, ook abs": "onovergankelijk werkwoord",
  "onpers ww": "onpersoonlijk werkwoord",
  "ww, alleen onbep w": "werkwoord (alleen onbepaalde wijs)",
  "wdk ww": "wederkerend werkwoord",
  "ww": "werkwoord",
  "hulpww": "hulpwerkwoord",
  "koppelww": "koppelwerkwoord",
  "vz": "voorzetsel",
  "vw": "voegwoord",
  "vnw": "voornaamwoord",
  "tw": "tussenwerpsel",
  "lidw": "lidwoord",
  "hoofdtelw": "hoofdtelwoord",
  "rangtelw": "rangtelwoord",
  "meervoud": "meervoud",
  "afk": "afkorting",
  "tussenwerpsel": "tussenwerpsel",
  "eigenn": "eigennaam",
};

export function posLabel(pos: string | null | undefined): string {
  if (!pos) return "";
  return POS_LABELS[pos] ?? pos;
}
