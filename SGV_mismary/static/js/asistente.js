document.addEventListener("DOMContentLoaded", function () {

    const personaje = document.getElementById("asistente-personaje");
    const invitacion = document.getElementById("asistente-invitacion");
    const ventana = document.getElementById("asistente-ventana");
    const cerrar = document.getElementById("asistente-cerrar");
    const formulario = document.getElementById("asistente-formulario");
    const entrada = document.getElementById("asistente-entrada");
    const mensajes = document.getElementById("asistente-mensajes");

    if (!personaje || !ventana || !formulario || !entrada || !mensajes) {
        return;
    }

    function abrirChat() {
        ventana.classList.add("abierto");

        if (invitacion) {
            invitacion.style.display = "none";
        }

        entrada.focus();
    }

    function cerrarChat() {
        ventana.classList.remove("abierto");
    }

    personaje.addEventListener("click", abrirChat);

    if (invitacion) {
        invitacion.addEventListener("click", abrirChat);
    }

    cerrar.addEventListener("click", cerrarChat);

    function normalizar(texto) {
        return texto.toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[¿?¡!,.;:]/g, "")
            .trim();
    }

    /* IMPORTANTE: gana la primera coincidencia.
       Las preguntas específicas van ANTES de las generales. */
    const respuestas = [

        /* ---------- Saludos ---------- */
        {
            palabras: ["hola", "buenos dias", "buenas tardes", "buenas noches", "buenas", "hey", "saludos", "como estas", "como vas"],
            respuesta: "¡Hola! Bienvenido a MisMary. Soy tu asistente virtual. ¿En qué puedo ayudarte?"
        },

        /* ---------- Preguntas específicas ---------- */
        {
            palabras: ["que pasa si elimino un pedido", "que pasa si se elimina un pedido", "eliminar pedido", "borrar pedido", "elimino un pedido", "pedido eliminado", "cancelar pedido"],
            respuesta: "Si eliminas un pedido, deja de aparecer en la lista de pedidos. Revisa bien antes de confirmar y verifica después el inventario."
        },
        {
            palabras: ["como funciona el inventario", "como funciona inventario", "como se actualiza el inventario", "actualizar inventario"],
            respuesta: "El inventario muestra cuántas unidades hay de cada producto. Se mantiene al día con las ventas y los pedidos que registras."
        },
        {
            palabras: ["como funcionan los abonos", "como registro un abono", "registrar abono", "hacer abono", "nuevo abono", "abonar"],
            respuesta: "Un abono es un pago parcial sobre una deuda. Regístralo en la deuda correspondiente y el saldo pendiente se actualiza."
        },
        {
            palabras: ["eliminar venta", "borrar venta", "anular venta", "elimino una venta"],
            respuesta: "Si una venta se hizo por error, revisa si tu usuario tiene permiso para eliminarla. Si no, pide ayuda al administrador."
        },
        {
            palabras: ["eliminar cliente", "borrar cliente", "elimino un cliente"],
            respuesta: "Puedes eliminar un cliente desde Clientes, si tu usuario tiene permiso. Revisa antes que no tenga deudas pendientes."
        },
        {
            palabras: ["eliminar proveedor", "borrar proveedor", "elimino un proveedor"],
            respuesta: "Puedes eliminar un proveedor desde Proveedores, si tu usuario tiene permiso. Revisa antes que no tenga pedidos pendientes."
        },
        {
            palabras: ["estado del pedido", "pedido pendiente", "pedido recibido", "pedido entregado"],
            respuesta: "En Pedidos puedes ver el estado de cada uno: si sigue pendiente o ya llegó."
        },
        {
            palabras: ["que es un reembolso", "como funciona el reembolso", "como funcionan los reembolsos"],
            respuesta: "Un reembolso es cuando un cliente devuelve un producto y se le regresa su dinero. Se registra desde Reembolsos."
        },

        /* ---------- Sobre el asistente ---------- */
        {
            palabras: ["que es mismary", "que es mis mary", "para que sirve mismary"],
            respuesta: "MisMary es un sistema de gestión de tienda que permite administrar productos, inventario, ventas, pedidos, proveedores y otros procesos."
        },
        {
            palabras: ["quien eres", "como te llamas", "que eres", "eres un robot", "eres real"],
            respuesta: "Soy Naranjita el asistente virtual de MisMary. Tengo respuestas preparadas para ayudarte a usar el sistema."
        },
        {
            palabras: ["que puedes hacer", "que haces", "para que sirves", "en que me ayudas"],
            respuesta: "Te oriento sobre productos, inventario, clientes, ventas, pedidos, proveedores, abonos, deudas, reembolsos y reportes."
        },

        /* ---------- Problemas y ayuda ---------- */
        {
            palabras: ["no entiendo", "estoy perdido", "estoy perdida", "no se que hacer", "no se como"],
            respuesta: "Tranquilo, te ayudo. Dime qué quieres hacer, por ejemplo \"registrar una venta\" o \"ver el inventario\"."
        },
        {
            palabras: ["cerrar sesion", "salir del sistema", "logout"],
            respuesta: "Abre el menú lateral (las tres rayitas) y pulsa el botón naranja \"Cerrar sesión\"."
        },
        {
            palabras: ["no me deja", "no puedo", "sin permiso", "no tengo acceso", "acceso denegado"],
            respuesta: "Seguramente tu usuario no tiene permiso para eso. Pídele al administrador que lo revise."
        },
        {
            palabras: ["error", "falla", "no funciona", "se dano"],
            respuesta: "Lamento el inconveniente. Recarga la página e intenta de nuevo. Si sigue igual, avisa al administrador."
        },

        /* ---------- Secciones (generales) ---------- */
        {
            palabras: ["productos", "producto", "catalogo", "ver productos", "consultar productos", "buscar productos"],
            respuesta: "Puedes consultar los productos desde la sección de productos del menú principal. Allí encontrarás la información disponible de cada uno."
        },
        {
            palabras: ["inventario", "stock", "existencias"],
            respuesta: "En la sección de inventario puedes revisar las cantidades disponibles y la información de los productos registrados."
        },
        {
            palabras: ["ventas", "venta", "registrar venta", "consultar ventas"],
            respuesta: "En la sección de ventas puedes consultar los registros y revisar la información de las ventas realizadas."
        },
        {
            palabras: ["pedidos", "pedido"],
            respuesta: "En la sección de pedidos puedes consultar los pedidos registrados, sus proveedores, fechas y estados."
        },
        {
            palabras: ["clientes", "cliente"],
            respuesta: "En Clientes puedes consultar la información de las personas registradas en el sistema."
        },
        {
            palabras: ["proveedores", "proveedor"],
            respuesta: "En proveedores puedes consultar la información de las personas o empresas que suministran productos a la tienda."
        },
        {
            palabras: ["abonos", "abono", "pagos"],
            respuesta: "Los abonos permiten registrar y consultar los pagos realizados sobre una deuda."
        },
        {
            palabras: ["deudas", "deuda", "saldo pendiente", "cuanto debe", "fiado", "fiar"],
            respuesta: "En la sección de deudas puedes revisar los saldos pendientes. Cada abono que registres reduce ese saldo."
        },
        {
            palabras: ["reembolso", "reembolsos", "devolucion", "devoluciones"],
            respuesta: "En reembolsos puedes consultar las solicitudes de devolución registradas y revisar su estado."
        },
        {
            palabras: ["reporte", "reportes", "informe", "informes"],
            respuesta: "En Reportes puedes consultar la información resumida que ofrece el sistema."
        },
        {
            palabras: ["grupo", "grupos", "permiso", "permisos", "roles"],
            respuesta: "La opción Grupos permite administrar los grupos y permisos. Está disponible únicamente para el superusuario."
        },
        {
            palabras: ["ayuda", "necesito ayuda", "como funciona"],
            respuesta: "¡Claro! Puedo orientarte sobre productos, inventario, clientes, ventas, pedidos, proveedores, abonos, deudas, reembolsos y reportes."
        },

        /* ---------- Cortesía y despedidas ---------- */
        {
            palabras: ["gracias", "muchas gracias", "te agradezco", "mil gracias"],
            respuesta: "¡Con mucho gusto! Estoy aquí para ayudarte."
        },
        {
            palabras: ["listo", "vale", "perfecto", "entendido"],
            respuesta: "¡Perfecto! Si necesitas algo más, aquí estoy."
        },
        {
            palabras: ["adios", "hasta luego", "chao", "chau", "nos vemos", "hasta pronto", "bye", "me voy"],
            respuesta: "¡Hasta luego! Gracias por utilizar MisMary."
        }
    ];

    function mostrarMensaje(texto, tipo) {
        const mensaje = document.createElement("div");
        mensaje.classList.add("asistente-mensaje", tipo);
        mensaje.textContent = texto;
        mensajes.appendChild(mensaje);
        mensajes.scrollTop = mensajes.scrollHeight;
    }

    function buscarRespuesta(texto) {
        const consulta = normalizar(texto);

        for (const elemento of respuestas) {
            const coincide = elemento.palabras.some(function (palabra) {
                const clave = normalizar(palabra);
                return consulta === clave || consulta.includes(clave);
            });

            if (coincide) {
                return elemento.respuesta;
            }
        }

        return "Lo siento, todavía no tengo una respuesta programada para esa pregunta. Puedes consultar las opciones del menú o comunicarte con un administrador de MisMary.";
    }

    function enviarMensaje(texto) {
        const pregunta = texto.trim();

        if (!pregunta) return;

        mostrarMensaje(pregunta, "usuario");

        const respuesta = buscarRespuesta(pregunta);

        window.setTimeout(function () {
            mostrarMensaje(respuesta, "bot");
        }, 350);

        entrada.value = "";
        entrada.focus();
    }

    formulario.addEventListener("submit", function (evento) {
        evento.preventDefault();
        enviarMensaje(entrada.value);
    });

    document.querySelectorAll(".asistente-sugerencia").forEach(function (boton) {
        boton.addEventListener("click", function () {
            enviarMensaje(boton.textContent);
        });
    });

    mostrarMensaje(
        "¡Hola! Soy el asistente virtual de MisMary. Puedes preguntarme sobre productos, inventario, ventas, pedidos y otras funciones de la tienda.",
        "bot"
    );

});