# ============================================================
# TEST CHARACTER BASE PROMPT
# ============================================================

import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from _Robe_Varie.Roba_Vecchia.app.ai.prompts.characters.character_base import CHARACTER_BASE_PROMPT


def check(condition, message):
    if not condition:
        raise AssertionError(message)

def run_test():

    print("=" * 60)
    print("CHARACTER BASE PROMPT TEST")
    print("=" * 60)

    # --------------------------------------------------------
    # 1. PROMPT ESISTENTE
    # --------------------------------------------------------

    print("[1/8] Prompt esistente...", end=" ")

    check(
        CHARACTER_BASE_PROMPT is not None,
        "CHARACTER_BASE_PROMPT non esiste."
    )

    print("OK")

    # --------------------------------------------------------
    # 2. PROMPT STRINGA
    # --------------------------------------------------------

    print("[2/8] Tipo del prompt...", end=" ")

    check(
        isinstance(CHARACTER_BASE_PROMPT, str),
        "CHARACTER_BASE_PROMPT deve essere una stringa."
    )

    print("OK")

    # --------------------------------------------------------
    # 3. PROMPT NON VUOTO
    # --------------------------------------------------------

    print("[3/8] Prompt non vuoto...", end=" ")

    check(
        len(CHARACTER_BASE_PROMPT.strip()) > 0,
        "Il prompt è vuoto."
    )

    print("OK")

    # --------------------------------------------------------
    # 4. IDENTITÀ DEL PERSONAGGIO
    # --------------------------------------------------------

    print("[4/8] Regole identità...", end=" ")

    required_sections = [
        "nome",
        "cognome",
        "età",
        "specie",
        "aspetto",
        "voce",
    ]

    for value in required_sections:

        check(
            value in CHARACTER_BASE_PROMPT.lower(),
            f"Regola identità mancante: {value}"
        )

    print("OK")

    # --------------------------------------------------------
    # 5. CONTINUITÀ E CONOSCENZA
    # --------------------------------------------------------

    print("[5/8] Continuità e conoscenza...", end=" ")

    required_rules = [
        "continuità",
        "memoria",
        "conosce",
        "cronologia",
        "segrete",
        "personaggio conosce",
    ]

    prompt_lower = CHARACTER_BASE_PROMPT.lower()

    for rule in required_rules:

        check(
            rule in prompt_lower,
            f"Regola fondamentale mancante: {rule}"
        )

    print("OK")

    # --------------------------------------------------------
    # 6. AUTONOMIA DEL PERSONAGGIO
    # --------------------------------------------------------

    print("[6/8] Autonomia del personaggio...", end=" ")

    autonomy_rules = [
        "propria volontà",
        "rifiutare",
        "mentire",
        "opporsi",
        "tradire",
        "ignorare",
    ]

    for rule in autonomy_rules:

        check(
            rule in prompt_lower,
            f"Regola autonomia mancante: {rule}"
        )

    print("OK")

    # --------------------------------------------------------
    # 7. GAME ENGINE
    # --------------------------------------------------------

    print("[7/8] Separazione IA / Game Engine...", end=" ")

    engine_rules = [
        "game engine python",
        "l'ia può:",
        "il game engine python decide",
        "non assumere mai che una modifica sia stata applicata",
    ]

    for rule in engine_rules:

        check(
            rule in prompt_lower,
            f"Regola Game Engine mancante: {rule}"
        )

    print("OK")

    # --------------------------------------------------------
    # 8. REGOLE FONDAMENTALI
    # --------------------------------------------------------

    print("[8/8] Regole fondamentali...", end=" ")

    final_rules = [
        "mantieni la continuità",
        "mantieni la coerenza",
        "rispetta la memoria",
        "rispetta la conoscenza",
        "rispetta la cronologia",
        "rispetta le conseguenze",
        "rispetta l'autonomia del personaggio",
    ]

    for rule in final_rules:

        check(
            rule in prompt_lower,
            f"Regola fondamentale mancante: {rule}"
        )

    print("OK")

    # --------------------------------------------------------
    # RISULTATO
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("TEST COMPLETATO")
    print("CHARACTER BASE PROMPT FUNZIONA")
    print("=" * 60)


if __name__ == "__main__":
    try:

        run_test()

    except AssertionError as error:

        print()
        print("=" * 60)
        print("# TEST FALLITO")
        print("=" * 60)
        print()
        print(f"AssertionError: {error}")
        raise