from _Robe_Varie.Roba_Vecchia.app.database import initialize_database, has_existing_game
from _Robe_Varie.Roba_Vecchia.app.game_setup import create_new_game
from _Robe_Varie.Roba_Vecchia.app.game_load import find_character_id_by_name
from _Robe_Varie.Roba_Vecchia.app.game_turn import process_turn


def start_game():

    # =========================================================
    # DATABASE
    # =========================================================

    initialize_database()

    # =========================================================
    # CARICAMENTO O CREAZIONE PARTITA
    # =========================================================

    lilith_id = None
    protagonist_id = None

    if has_existing_game():

        print()
        print("È stata trovata una partita salvata.")

        scelta = input(
            "Vuoi continuare (c) o iniziare una nuova partita (n)? "
        ).strip().lower()

        if scelta != "n":

            lilith_id = find_character_id_by_name("Lilith")
            protagonist_id = find_character_id_by_name("Protagonista")

    if lilith_id is None or protagonist_id is None:

        game = create_new_game()

        lilith_id = game["lilith_id"]
        protagonist_id = game["protagonist_id"]

    print()
    print("========================================")
    print("RPG AVVIATO")
    print("========================================")
    print()
    print("Lilith è pronta.")
    print("Scrivi 'esci' per terminare.")
    print()

    # =========================================================
    # GAME LOOP
    # =========================================================

    while True:

        player_input = input("Tu: ").strip()

        if not player_input:
            continue

        # =====================================================
        # USCITA
        # =====================================================

        if player_input.lower() == "esci":

            print()
            print("Partita terminata.")
            break

        # =====================================================
        # ELABORAZIONE TURNO
        # =====================================================

        try:

            result = process_turn(
                reacting_character_id=lilith_id,
                player_id=protagonist_id,
                player_input=player_input
            )

        except Exception as error:

            print()
            print("ERRORE IMPREVISTO DURANTE IL TURNO")
            print()
            print(f"Dettagli: {error}")
            print()

            continue

        print()

        # =====================================================
        # ERRORE
        # =====================================================

        if not result.get("success", False):

            print("ERRORE DURANTE IL TURNO")
            print()
            print(result)
            print()

            continue

        # =====================================================
        # NARRAZIONE
        # =====================================================

        print("Lilith:")
        print(result.get("narration", ""))

        print()


# =========================================================
# AVVIO
# =========================================================

if __name__ == "__main__":
    start_game()