---
type: notes
title: "Uživatelský manuál"
status: approved
summary: "Pack je hotové nastavení pro **Claude Code (CC)** - terminálovou appku od Anthropic, která umí dělat věci na tvém počítači (psát soubory, spouštět příkazy, instalovat prakticky cokoliv)."
created: 2026-06-10 00:00
updated: 2026-06-10 00:00
owner: Šimon Hradní
client: ~
path: UZIVATELSKY-MANUAL.md
tags: [note]
version: "1.0.0"
release: latest
---

# Uživatelský manuál

Pack je hotové nastavení pro **Claude Code (CC)** — terminálovou appku od Anthropic, která umí dělat věci na tvém počítači (psát soubory, spouštět příkazy, instalovat prakticky cokoliv). Tento starter pack CC nakonfiguruje tak, aby ti omylem nesmazal disk a nezasahoval do citlivých věcí.

## Než půjdeš dál

**Claude Code není chat.** Na claude.ai napíšeš zprávu, dostaneš odpověď, na disku se nic neděje. V Claude Code napíšeš úkol a Claude reálně edituje soubory, spouští příkazy, instaluje věci. Tento starter pack je pojistka, aby to (ve většině případů) nedopadlo špatně.

## Instalace 

Odkaz na toto repo dej do CC a řekni mu, aby si to načetl a postupoval podle `INSTRUCTIONS.md`.

Claude si přečte `INSTRUCTIONS.md` a provede tě celým nastavením otázku po otázce. **Každý krok schvaluješ ty.** Pokud máš stávající nastavení, CC ho zálohuje, nepřepisuje.

## Pět věcí, které si zapamatuj

1. **Číst plán dřív, než řekneš „ano".** Většina chyb vzniká z odsouhlasení nečteného plánu.
2. **Když Claude něco nesmí, neobcházej to.** Řekni mu cíl, ne work-around. Navrhne bezpečnější cestu nebo ti dá příkaz k ručnímu spuštění.
3. **API klíče dej do `~/.claude/.env`.** Claude tam nevidí — pracuje s názvy, ne hodnotami.
4. **Statusbar dole ti říká důležité informace o dané session.** Mimo jiné stav kontextového okna a kolik by tě session stála, kdybys platil za tokeny.
5. **Pro každý nový projekt napiš `/setup`.** Vytvoří složky a šablony.

## Když něco nejde

| Situace | Co dělat |
|---------|----------|
| Claude opakuje stejnou chybu | Ukonči (`Ctrl+D`), nová session |
| Statusbar svítí červeně | Pauza, nebo to dodělej na claude.ai |
| Claude chce dělat něco divného | Zeptej se: *„Co přesně chceš udělat? Ještě to nedělej."* |
| Po instalaci nevidím staré nastavení | Není pryč — záloha v `~/.claude.bak-<datum>/` |

## Kam dál

- **`README.md`** — co Pack obsahuje
- **`INSTRUCTIONS.md`** — instalační skript pro Claude (ty ho nečteš, on ho čte)
