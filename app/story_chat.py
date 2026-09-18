from __future__ import annotations
import json
from app.ai_provider import ask_ollama
from app.database.characters_db import get_character, save_character

def _clean_history(extra):
    h=extra.get("story_chat",[]) if isinstance(extra,dict) else []
    if not isinstance(h,list): return []
    return [x for x in h if isinstance(x,dict) and x.get("role") in ("user","assistant") and isinstance(x.get("content"),str) and x["content"].strip()][-24:]

def get_story_history(character_id:int):
    c=get_character(character_id)
    if c is None: raise ValueError(f"Personaggio con ID {character_id} non trovato.")
    return _clean_history(c.get("extra",{}))

def reset_story_history(character_id:int):
    c=get_character(character_id)
    if c is None: raise ValueError(f"Personaggio con ID {character_id} non trovato.")
    extra=c.get("extra",{})
    if not isinstance(extra,dict): extra={}
    extra.pop("story_chat",None)
    save_character(c["identity"],c["languages"],extra_data=extra,character_id=character_id)

def story_turn(character_id:int, player_message:str):
    c=get_character(character_id)
    if c is None: raise ValueError(f"Personaggio con ID {character_id} non trovato.")
    message=player_message.strip()
    if not message: raise ValueError("Il messaggio non può essere vuoto.")
    extra=c.get("extra",{})
    if not isinstance(extra,dict): extra={}
    history=_clean_history(extra)
    i=c["identity"]
    character=json.dumps({
        "name":i.name,"surname":i.surname,"age":i.age,"sex":i.sex,"race":i.race,
        "physical_description":i.physical_description,"appearance":i.appearance,
        "psychology":extra.get("psychology",{}),"personality":extra.get("personality",{}),
        "statistics":extra.get("statistics",{}),"abilities":extra.get("abilities",[]),
        "skills":extra.get("skills",[]),"conditions":extra.get("conditions",{}),
        "inventory":extra.get("inventory",{}),"magic":extra.get("magic",{})
    },ensure_ascii=False)
    system=f"""Sei il Game Master di un RPG narrativo in italiano.
Il giocatore interpreta {i.name}. Il giocatore può tentare QUALSIASI azione plausibile e può cambiare la storia.
Non decidere mai al posto del giocatore cosa pensa, prova, dice o fa. Descrivi invece il mondo, gli NPC e le conseguenze delle sue azioni.
Non usare menu A/B/C e non forzare una trama prestabilita. Se un'azione è rischiosa, può fallire. Mantieni continuità con la cronologia.
Non inventare capacità o oggetti del personaggio non presenti nel profilo.
Scrivi una risposta naturale, concreta e coinvolgente, in italiano. Di norma 1-4 paragrafi.
PROFILO DEL PERSONAGGIO:
{character}
Restituisci esclusivamente JSON valido nel formato {{"narration":"testo"}}."""
    prompt=json.dumps({"history":history,"player_message":message},ensure_ascii=False)
    raw=ask_ollama(system,prompt)
    try: result=json.loads(raw)
    except json.JSONDecodeError as e: raise ValueError("L'IA ha restituito una risposta non valida.") from e
    narration=result.get("narration")
    if not isinstance(narration,str) or not narration.strip(): raise ValueError("L'IA non ha restituito una narrazione.")
    history=(history+[{"role":"user","content":message},{"role":"assistant","content":narration.strip()}])[-24:]
    extra["story_chat"]=history
    save_character(c["identity"],c["languages"],extra_data=extra,character_id=character_id)
    return {"narration":narration.strip(),"conversation":history}
