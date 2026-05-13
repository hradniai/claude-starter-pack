# Uživatelský manuál

Pro někoho, jehož zkušenost s AI končí na claude.ai. Přečteš za půl minuty.

## Co to je

Pack je hotové nastavení pro **Claude Code** — terminálovou appku od Anthropic, která umí dělat věci na tvém počítači (psát soubory, spouštět příkazy, instalovat balíky). Pack ji nakonfiguruje tak, aby ti omylem nesmazala disk a nezasahovala do citlivých věcí.

## Pochop, než jdeš dál

**Claude Code není chat.** Na claude.ai napíšeš zprávu, dostaneš odpověď, na disku se nic neděje. V Claude Code napíšeš úkol a Claude reálně edituje soubory, spouští příkazy, instaluje věci. Když mu řekneš „ukliď tu složku", může to vyhodnotit jako „smaž ji."

Pack je pojistka, aby to nedopadlo špatně.

## Instalace (tři řádky)

```
git clone https://github.com/Gillellbor/claude-starter-pack.git ~/Downloads/pack
cd ~/Downloads/pack
claude
```

Claude si přečte `INSTRUCTIONS.md` a provede tě zbytkem otázku po otázce. **Každý krok schvaluješ ty.** Pokud máš stávající nastavení, Pack ho zálohuje, nepřepisuje.

Na Windows: nainstaluj WSL2, pak to dělej uvnitř něj. Nativní Windows nedoporučuju.

## Pět věcí, které si zapamatuj

1. **Číst plán dřív, než řekneš „ano".** Většina chyb vzniká z odsouhlasení nečteného plánu.
2. **Když Claude něco nesmí, neobcházej to.** Řekni mu cíl, ne work-around. Navrhne bezpečnější cestu nebo ti dá příkaz k ručnímu spuštění.
3. **API klíče dej do `~/.claude/.env`.** Claude tam nevidí — pracuje s názvy, ne hodnotami.
4. **Statusbar dole ti říká, kolik jsi utratil.** Červená = brzdi.
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
