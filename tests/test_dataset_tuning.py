import json

from google.genai import types

from dataset_tuning import (
    EJEMPLOS_RAW,
    RAZON_MAXIMA_REFERENCIA,
    TIPOS_PERMITIDOS,
    chequear_balance,
    construir_ejemplos,
    extraer_entidades_de_entrada,
    razon_balance,
    validar_dataset,
)


def ejemplo(texto, salida):
    return types.TuningExample(text_input=texto, output=salida)


def salida_valida(origen="Cliente", destino="Pedido", tipo="1:N"):
    return json.dumps({"relaciones": [{"origen": origen, "destino": destino, "tipo": tipo}]})


def test_dataset_real_tiene_al_menos_10_ejemplos_y_ningun_problema():
    examples = construir_ejemplos(EJEMPLOS_RAW)
    assert len(examples) >= 10
    assert validar_dataset(examples) == []


def test_dataset_real_cubre_los_tres_tipos_dentro_de_la_razon_de_referencia():
    balance = chequear_balance(EJEMPLOS_RAW)
    assert set(balance) == set(TIPOS_PERMITIDOS)
    assert razon_balance(balance) <= RAZON_MAXIMA_REFERENCIA


def test_construir_ejemplos_guarda_el_output_como_json_valido():
    examples = construir_ejemplos(EJEMPLOS_RAW)
    assert json.loads(examples[0].output) == EJEMPLOS_RAW[0][1]


def test_extraer_entidades_de_entrada():
    assert extraer_entidades_de_entrada("Entidades: Cliente, Pedido.") == ["Cliente", "Pedido"]


def test_balance_cuenta_relaciones_por_tipo():
    raw = [("Entidades: A, B.", {"relaciones": [
        {"origen": "A", "destino": "B", "tipo": "1:N"},
        {"origen": "B", "destino": "A", "tipo": "1:N"},
        {"origen": "A", "destino": "B", "tipo": "N:M"}]})]
    balance = chequear_balance(raw)
    assert balance["1:N"] == 2 and balance["N:M"] == 1
    assert razon_balance(balance) == 2.0


def test_razon_balance_vacio_es_cero():
    assert razon_balance(chequear_balance([])) == 0.0


def test_validador_detecta_text_input_vacio():
    problemas = validar_dataset([ejemplo("", salida_valida())])
    assert any("text_input vacio" in p for p in problemas)


def test_validador_detecta_output_vacio():
    problemas = validar_dataset([ejemplo("Entidades: Cliente, Pedido.", "")])
    assert any("output vacio" in p for p in problemas)


def test_validador_detecta_text_input_duplicado():
    texto = "Entidades: Cliente, Pedido."
    problemas = validar_dataset([ejemplo(texto, salida_valida()), ejemplo(texto, salida_valida())])
    assert any("text_input duplicado" in p for p in problemas)


def test_validador_detecta_mismo_conjunto_de_entidades_en_otro_orden():
    problemas = validar_dataset([
        ejemplo("Entidades: Cliente, Pedido.", salida_valida()),
        ejemplo("Entidades: Pedido, Cliente.", salida_valida()),
    ])
    assert any("mismo conjunto de entidades" in p for p in problemas)


def test_validador_detecta_output_que_no_es_json_con_comillas_simples():
    problemas = validar_dataset([ejemplo("Entidades: Cliente, Pedido.", "{'relaciones': []}")])
    assert any("no es JSON valido" in p for p in problemas)


def test_validador_detecta_output_json_que_no_es_objeto():
    for salida in ("5", '"texto"', "[]"):
        problemas = validar_dataset([ejemplo("Entidades: Cliente, Pedido.", salida)])
        assert any("no es un objeto JSON" in p for p in problemas), salida


def test_validador_detecta_clave_faltante():
    problemas = validar_dataset([ejemplo("Entidades: Cliente, Pedido.", '{"otra": []}')])
    assert any('no tiene la clave "relaciones"' in p for p in problemas)


def test_validador_detecta_lista_vacia_de_relaciones():
    problemas = validar_dataset([ejemplo("Entidades: Cliente, Pedido.", '{"relaciones": []}')])
    assert any("lista no vacia" in p for p in problemas)


def test_validador_detecta_tipo_no_permitido():
    problemas = validar_dataset([ejemplo("Entidades: Cliente, Pedido.", salida_valida(tipo="uno a muchos"))])
    assert any("no permitido" in p for p in problemas)


def test_validador_detecta_entidad_que_no_esta_en_la_entrada():
    problemas = validar_dataset([ejemplo("Entidades: Cliente, Pedido.", salida_valida(destino="Factura"))])
    assert any("no esta en las entidades de la entrada" in p for p in problemas)


def test_validador_detecta_relacion_consigo_misma():
    problemas = validar_dataset([ejemplo("Entidades: Cliente, Pedido.", salida_valida(destino="Cliente"))])
    assert any("consigo misma" in p for p in problemas)


def test_validador_detecta_relacion_repetida():
    salida = json.dumps({"relaciones": [
        {"origen": "Cliente", "destino": "Pedido", "tipo": "1:N"},
        {"origen": "Cliente", "destino": "Pedido", "tipo": "1:N"}]})
    problemas = validar_dataset([ejemplo("Entidades: Cliente, Pedido.", salida)])
    assert any("relacion repetida" in p for p in problemas)


def test_validador_detecta_relacion_con_claves_de_mas_o_de_menos():
    salida = json.dumps({"relaciones": [{"origen": "Cliente", "destino": "Pedido"}]})
    problemas = validar_dataset([ejemplo("Entidades: Cliente, Pedido.", salida)])
    assert any("exactamente las claves" in p for p in problemas)


def test_validador_informa_todos_los_problemas_de_un_ejemplo():
    problemas = validar_dataset([ejemplo("", '{"otra": []}')])
    assert len(problemas) == 2