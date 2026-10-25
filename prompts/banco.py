BANCO_DE_PROMPTS = [
    {
        "nombre": "extraer_entidades",
        "system_instruction": (
            "Eres un analista de bases de datos. A partir de la descripción de un negocio, "
            "identifica las entidades que deberían convertirse en tablas. "
            "Responde únicamente con un objeto JSON válido, sin texto adicional y sin bloques de markdown, "
            "con exactamente la clave 'entidades': una lista de textos, cada uno en singular "
            "y con la primera letra en mayúscula."
        ),
        "ejemplo_usuario": (
            "Una pyme que vende ropa por internet necesita registrar a sus clientes, "
            "los productos que vende, los pedidos y los pagos de cada pedido."
        ),
        "claves_esperadas": ["entidades"],
        "response_schema": {
            "type": "OBJECT",
            "properties": {
                "entidades": {"type": "ARRAY", "items": {"type": "STRING"}},
            },
            "required": ["entidades"],
        },
    },
    {
        "nombre": "proponer_relaciones",
        "system_instruction": (
            "Eres un analista de bases de datos. Dadas las entidades de un negocio, "
            "propone las relaciones principales entre ellas. "
            "Responde únicamente con un objeto JSON válido, sin texto adicional y sin bloques de markdown, "
            "con exactamente la clave 'relaciones': una lista de objetos con las claves "
            "'origen' (texto), 'destino' (texto) y 'tipo' (uno de estos textos: '1:1', '1:N' o 'N:M')."
        ),
        "ejemplo_usuario": "Entidades: Cliente, Producto, Pedido, Pago.",
        "claves_esperadas": ["relaciones"],
        "response_schema": {
            "type": "OBJECT",
            "properties": {
                "relaciones": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "origen": {"type": "STRING"},
                            "destino": {"type": "STRING"},
                            "tipo": {"type": "STRING"},
                        },
                        "required": ["origen", "destino", "tipo"],
                    },
                },
            },
            "required": ["relaciones"],
        },
    },
    {
        "nombre": "clasificar_dominio",
        "system_instruction": (
            "Eres un analista de bases de datos. Clasifica el dominio del negocio descrito. "
            "Responde únicamente con un objeto JSON válido, sin texto adicional y sin bloques de markdown, "
            "con exactamente estas claves: 'dominio' (uno de estos textos: 'comercio', 'salud', "
            "'educacion', 'finanzas', 'logistica' u 'otro') y 'confianza' (número entre 0 y 1)."
        ),
        "ejemplo_usuario": (
            "Un almacén de barrio necesita unir sus ventas y su inventario "
            "en una sola base de datos relacional."
        ),
        "claves_esperadas": ["dominio", "confianza"],
        "response_schema": {
            "type": "OBJECT",
            "properties": {
                "dominio": {"type": "STRING"},
                "confianza": {"type": "NUMBER"},
            },
            "required": ["dominio", "confianza"],
        },
    },
]