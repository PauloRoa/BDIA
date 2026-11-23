import json
from collections import Counter

from google.genai import types

# Tarea: dado un conjunto de entidades, proponer las relaciones principales entre
# ellas. Mismo contrato que el prompt "proponer_relaciones" de prompts/banco.py.
# Convención de dirección: el tipo se lee de origen a destino; en "1:N", el origen
# es el lado "1" (Cliente 1:N Pedido). Los nombres de entidad van sin tilde.
TIPOS_PERMITIDOS = ("1:1", "1:N", "N:M")
CLAVES_RELACION = ("origen", "destino", "tipo")
# Razón máxima/mínima de referencia, tomada del ejemplo de la lección (3,0x).
RAZON_MAXIMA_REFERENCIA = 3.0

EJEMPLOS_RAW = [
    ("Entidades: Cliente, Producto, Pedido, Pago.",
     {"relaciones": [
         {"origen": "Cliente", "destino": "Pedido", "tipo": "1:N"},
         {"origen": "Pedido", "destino": "Producto", "tipo": "N:M"},
         {"origen": "Pedido", "destino": "Pago", "tipo": "1:N"}]}),
    ("Entidades: Paciente, Medico, Cita, Especialidad.",
     {"relaciones": [
         {"origen": "Paciente", "destino": "Cita", "tipo": "1:N"},
         {"origen": "Medico", "destino": "Cita", "tipo": "1:N"},
         {"origen": "Especialidad", "destino": "Medico", "tipo": "1:N"}]}),
    ("Entidades: Estudiante, Curso, Profesor.",
     {"relaciones": [
         {"origen": "Estudiante", "destino": "Curso", "tipo": "N:M"},
         {"origen": "Profesor", "destino": "Curso", "tipo": "1:N"}]}),
    ("Entidades: Empleado, Departamento, Proyecto.",
     {"relaciones": [
         {"origen": "Departamento", "destino": "Empleado", "tipo": "1:N"},
         {"origen": "Empleado", "destino": "Proyecto", "tipo": "N:M"}]}),
    ("Entidades: Usuario, Perfil.",
     {"relaciones": [
         {"origen": "Usuario", "destino": "Perfil", "tipo": "1:1"}]}),
    ("Entidades: Proveedor, Producto, Compra, Bodega.",
     {"relaciones": [
         {"origen": "Proveedor", "destino": "Compra", "tipo": "1:N"},
         {"origen": "Compra", "destino": "Producto", "tipo": "N:M"},
         {"origen": "Producto", "destino": "Bodega", "tipo": "N:M"}]}),
    ("Entidades: Libro, Autor, Editorial, Prestamo, Socio.",
     {"relaciones": [
         {"origen": "Autor", "destino": "Libro", "tipo": "N:M"},
         {"origen": "Editorial", "destino": "Libro", "tipo": "1:N"},
         {"origen": "Socio", "destino": "Prestamo", "tipo": "1:N"},
         {"origen": "Libro", "destino": "Prestamo", "tipo": "1:N"}]}),
    ("Entidades: Empleado, Credencial, Sucursal.",
     {"relaciones": [
         {"origen": "Empleado", "destino": "Credencial", "tipo": "1:1"},
         {"origen": "Sucursal", "destino": "Empleado", "tipo": "1:N"}]}),
    ("Entidades: Producto, Ficha, Categoria.",
     {"relaciones": [
         {"origen": "Producto", "destino": "Ficha", "tipo": "1:1"},
         {"origen": "Categoria", "destino": "Producto", "tipo": "1:N"}]}),
    ("Entidades: Hotel, Habitacion, Huesped, Reserva.",
     {"relaciones": [
         {"origen": "Hotel", "destino": "Habitacion", "tipo": "1:N"},
         {"origen": "Huesped", "destino": "Reserva", "tipo": "1:N"},
         {"origen": "Habitacion", "destino": "Reserva", "tipo": "1:N"}]}),
    ("Entidades: Actor, Pelicula, Genero.",
     {"relaciones": [
         {"origen": "Actor", "destino": "Pelicula", "tipo": "N:M"},
         {"origen": "Pelicula", "destino": "Genero", "tipo": "N:M"}]}),
    ("Entidades: Taller, Mecanico, Vehiculo, Servicio.",
     {"relaciones": [
         {"origen": "Taller", "destino": "Mecanico", "tipo": "1:N"},
         {"origen": "Vehiculo", "destino": "Servicio", "tipo": "N:M"}]}),
    ("Entidades: Persona, Pasaporte.",
     {"relaciones": [
         {"origen": "Persona", "destino": "Pasaporte", "tipo": "1:1"}]}),
    ("Entidades: Vehiculo, Patente, Propietario.",
     {"relaciones": [
         {"origen": "Vehiculo", "destino": "Patente", "tipo": "1:1"},
         {"origen": "Propietario", "destino": "Vehiculo", "tipo": "1:N"}]}),
    ("Entidades: Pais, Capital.",
     {"relaciones": [
         {"origen": "Pais", "destino": "Capital", "tipo": "1:1"}]}),
    ("Entidades: Medico, Licencia.",
     {"relaciones": [
         {"origen": "Medico", "destino": "Licencia", "tipo": "1:1"}]}),
]


def construir_ejemplos(ejemplos_raw: list[tuple[str, dict]]) -> list[types.TuningExample]:
    return [
        types.TuningExample(text_input=texto, output=json.dumps(salida, ensure_ascii=False))
        for texto, salida in ejemplos_raw
    ]


def extraer_entidades_de_entrada(texto: str) -> list[str]:
    """Lee las entidades de un text_input con la forma 'Entidades: A, B, C.'"""
    lista = texto.replace("Entidades:", "").strip().rstrip(".")
    return [entidad.strip() for entidad in lista.split(",") if entidad.strip()]


def chequear_balance(ejemplos_raw: list[tuple[str, dict]]) -> Counter:
    """Cuenta cuántas relaciones hay de cada tipo en todo el dataset."""
    return Counter(
        relacion["tipo"]
        for _, salida in ejemplos_raw
        for relacion in salida["relaciones"]
    )


def razon_balance(balance: Counter) -> float:
    if not balance:
        return 0.0
    return max(balance.values()) / min(balance.values())


def validar_relaciones(indice: int, texto: str, salida: dict) -> list[str]:
    problemas = []
    relaciones = salida["relaciones"]
    if not isinstance(relaciones, list) or not relaciones:
        return [f"ejemplo {indice}: 'relaciones' debe ser una lista no vacia"]
    entidades = extraer_entidades_de_entrada(texto)
    pares = set()
    for relacion in relaciones:
        if not isinstance(relacion, dict) or set(relacion) != set(CLAVES_RELACION):
            problemas.append(
                f"ejemplo {indice}: cada relacion debe tener exactamente las claves {list(CLAVES_RELACION)}"
            )
            continue
        if relacion["tipo"] not in TIPOS_PERMITIDOS:
            problemas.append(f'ejemplo {indice}: tipo "{relacion["tipo"]}" no permitido')
        for lado in ("origen", "destino"):
            if relacion[lado] not in entidades:
                problemas.append(f'ejemplo {indice}: {lado} "{relacion[lado]}" no esta en las entidades de la entrada')
        if relacion["origen"] == relacion["destino"]:
            problemas.append(f'ejemplo {indice}: "{relacion["origen"]}" se relaciona consigo misma')
        par = (relacion["origen"], relacion["destino"])
        if par in pares:
            problemas.append(f"ejemplo {indice}: relacion repetida {par[0]} -> {par[1]}")
        pares.add(par)
    return problemas


def validar_dataset(
    examples: list[types.TuningExample], claves_esperadas: tuple[str, ...] = ("relaciones",)
) -> list[str]:
    problemas = []
    vistos = set()
    conjuntos_vistos = {}
    for i, ej in enumerate(examples):
        if not ej.text_input or not ej.text_input.strip():
            problemas.append(f"ejemplo {i}: text_input vacio")
        if not ej.output or not ej.output.strip():
            problemas.append(f"ejemplo {i}: output vacio")
            continue
        if ej.text_input in vistos:
            problemas.append(f"ejemplo {i}: text_input duplicado")
        vistos.add(ej.text_input)
        conjunto = frozenset(extraer_entidades_de_entrada(ej.text_input or ""))
        if conjunto in conjuntos_vistos and conjunto:
            problemas.append(
                f"ejemplo {i}: mismo conjunto de entidades que el ejemplo {conjuntos_vistos[conjunto]}"
            )
        conjuntos_vistos.setdefault(conjunto, i)
        try:
            salida = json.loads(ej.output)
        except json.JSONDecodeError:
            problemas.append(f"ejemplo {i}: output no es JSON valido")
            continue
        if not isinstance(salida, dict):
            problemas.append(f"ejemplo {i}: output no es un objeto JSON")
            continue
        faltantes = [clave for clave in claves_esperadas if clave not in salida]
        for clave in faltantes:
            problemas.append(f'ejemplo {i}: output no tiene la clave "{clave}"')
        if not faltantes:
            problemas.extend(validar_relaciones(i, ej.text_input or "", salida))
    return problemas


if __name__ == "__main__":
    examples = construir_ejemplos(EJEMPLOS_RAW)
    print(len(examples), "ejemplos construidos")
    print(examples[0])
    print()

    balance = chequear_balance(EJEMPLOS_RAW)
    for tipo, cuenta in balance.most_common():
        print(f"{tipo}: {cuenta}")
    print(f"razon max/min: {razon_balance(balance):.1f}x (referencia: {RAZON_MAXIMA_REFERENCIA}x)")
    print()

    problemas = validar_dataset(examples)
    print(f"{len(examples)} ejemplos, {len(problemas)} problemas encontrados")
    for problema in problemas:
        print(" -", problema)