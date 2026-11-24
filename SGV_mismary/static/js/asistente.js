/* =====================================================================
   ASISTENTE VIRTUAL "NARANJITA" · MisMary
   Archivo: static/js/asistente.js

   Está dividido en 8 partes, en este orden:
     1. Elementos de la página
     2. Animaciones de Naranjita (el muñeco 3D)
     3. Abrir y cerrar el chat
     4. Funciones para limpiar texto
     5. Respuestas predeterminadas (aquí agregas preguntas nuevas)
     6. Calculadora
     7. Mensajes del chat
     8. Voz (hablarle a Naranjita)
   ===================================================================== */

document.addEventListener("DOMContentLoaded", function () {

    /* =================================================================
       1. ELEMENTOS DE LA PÁGINA
       ================================================================= */
    const personaje = document.getElementById("asistente-personaje");
    const invitacion = document.getElementById("asistente-invitacion");
    const ventana = document.getElementById("asistente-ventana");
    const cerrar = document.getElementById("asistente-cerrar");
    const formulario = document.getElementById("asistente-formulario");
    const entrada = document.getElementById("asistente-entrada");
    const mensajes = document.getElementById("asistente-mensajes");
    const microfono = document.getElementById("asistente-microfono");

    /* Si falta algo importante, no hacemos nada para no romper la página */
    if (!personaje || !ventana || !formulario || !entrada || !mensajes) {
        return;
    }

    const modelo = personaje.querySelector("model-viewer");

    /* Las rutas de las páginas llegan desde base.html */
    const RUTAS = window.RUTAS_VOZ || { registrar: {} };


    /* =================================================================
       2. ANIMACIONES DE NARANJITA
       Animaciones del modelo: Reposo, Saludar, Hablar, Brincar, Caminar
       ================================================================= */
    const sinMovimiento = window.matchMedia &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    /* Cuántos segundos dura cada animación (para volver a Reposo) */
    const DURACION = { Saludar: 3, Hablar: 1.2, Brincar: 1, Caminar: 1 };
    let temporizadorAnimacion = null;

    /* ¿Se puede reproducir esta animación ahora mismo? */
    function puedeAnimar(nombre) {
        return !sinMovimiento &&
            modelo &&
            modelo.loaded &&
            typeof modelo.play === "function" &&
            Array.isArray(modelo.availableAnimations) &&
            modelo.availableAnimations.indexOf(nombre) !== -1;
    }

    /* Reposo: respira y mueve los brazos despacio, sin parar */
    function reposo() {
        window.clearTimeout(temporizadorAnimacion);
        if (!puedeAnimar("Reposo")) return;
        modelo.animationName = "Reposo";
        modelo.play({ repetitions: Infinity });
    }

    /* Hace una animación unas cuantas veces y luego vuelve a Reposo */
    function animar(nombre, veces) {
        if (!puedeAnimar(nombre)) return;
        veces = veces || 1;
        modelo.animationName = nombre;
        modelo.play({ repetitions: veces });

        window.clearTimeout(temporizadorAnimacion);
        temporizadorAnimacion = window.setTimeout(
            reposo,
            ((DURACION[nombre] || 2) * veces + 0.4) * 1000
        );
    }

    /* Cuando termina una animación, vuelve a Reposo */
    if (modelo) {
        modelo.addEventListener("finished", reposo);

        modelo.addEventListener("load", function () {
            reposo();
            window.setTimeout(saludoAutomatico, 1500);
        });

        /* Si el modelo ya estaba cargado cuando corrió este script */
        if (modelo.loaded) {
            reposo();
        }
    }

    /* Saluda sola, pero máximo 3 veces por pestaña */
    const MAX_SALUDOS = 3;

    function saludoAutomatico() {
        if (ventana.classList.contains("abierto")) return;

        let hechos = 0;
        try {
            hechos = parseInt(sessionStorage.getItem("naranjitaSaludos") || "0", 10) || 0;
        } catch (e) {}

        if (hechos >= MAX_SALUDOS) return;

        try { sessionStorage.setItem("naranjitaSaludos", String(hechos + 1)); } catch (e) {}
        animar("Saludar");
    }

    /* Mientras el chat está cerrado, intenta saludar cada 40 segundos */
    window.setInterval(saludoAutomatico, 40000);

    /* Mueve los brazos mientras "habla", según el largo del texto */
    function hablar(texto) {
        const milisegundos = Math.min(6000, Math.max(1500, texto.length * 50));
        animar("Hablar", Math.max(2, Math.round(milisegundos / 1200)));
    }


    /* =================================================================
       3. ABRIR Y CERRAR EL CHAT
       ================================================================= */
    function abrirChat() {
        const yaEstabaAbierto = ventana.classList.contains("abierto");
        ventana.classList.add("abierto");

        if (invitacion) invitacion.style.display = "none";

        entrada.focus();

        if (!yaEstabaAbierto) animar("Saludar");
    }

    function cerrarChat() {
        ventana.classList.remove("abierto");
        reposo();
    }

    personaje.addEventListener("click", abrirChat);
    if (invitacion) invitacion.addEventListener("click", abrirChat);
    if (cerrar) cerrar.addEventListener("click", cerrarChat);

    /* Si venimos de un comando de voz, el chat sigue abierto en la página nueva */
    try {
        if (sessionStorage.getItem("naranjitaAbierto") === "1") {
            sessionStorage.removeItem("naranjitaAbierto");
            ventana.classList.add("abierto");
            if (invitacion) invitacion.style.display = "none";
        }
    } catch (e) {}


    /* =================================================================
       4. FUNCIONES PARA LIMPIAR TEXTO
       Quitan mayúsculas, tildes y signos para comparar más fácil.
       Ejemplo: "¿Cómo estás?"  →  "como estas"
       ================================================================= */
    function normalizar(texto) {
        return texto.toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[¿?¡!,.;:]/g, "")
            .trim();
    }

    /* ¿El texto contiene alguna de estas palabras completas? */
    function contiene(texto, lista) {
        const t = " " + normalizar(texto) + " ";
        return lista.some(function (palabra) {
            return t.indexOf(" " + palabra + " ") !== -1;
        });
    }

    /* Primera letra en mayúscula */
    function capitalizar(texto) {
        return texto.charAt(0).toUpperCase() + texto.slice(1);
    }


    /* =================================================================
       5. RESPUESTAS PREDETERMINADAS
       IMPORTANTE: gana la PRIMERA coincidencia.
       Las preguntas específicas van ANTES de las generales.

       Para agregar una pregunta nueva, copia un bloque así:
         {
             palabras: ["frase 1", "frase 2"],     (sin tildes ni signos)
             respuesta: "Texto de la respuesta"
         },
       Si "respuesta" es una lista [ ... ], Naranjita elige una al azar.
       ================================================================= */
    const respuestas = [

        /* ---------- Conversación ---------- */
        {
            palabras: ["como estas", "como vas", "como te va", "como amaneciste", "como andas", "como te sientes", "como esta usted"],
            respuesta: [
                "Por ahora estoy bien, gracias por preguntar 🍊. ¿Y tú cómo estás? ¿En qué te puedo ayudar?",
                "¡Todo bien por acá, jugosa y lista! Cuéntame, ¿tú cómo vas y qué necesitas?",
                "Bien, bien, aquí dándole duro al trabajo. Pero dime tú, ¿cómo estás y en qué te colaboro?"
            ]
        },
        {
            palabras: ["consejo del dia", "dame un consejo", "dame el consejo", "dame consejo", "un consejo", "consejo para hoy", "consejito"],
            respuesta: [
                "Consejo del día: si quiere ser feliz, mande a comer monda a todo el que le amargue la vida. Eso sí, con cariño, que somos gente educada 😄.",
                "Consejo del día: el que madruga Dios lo ayuda, pero el que fía sin anotar queda en la ruina. ¡Anote todo en MisMary, parce!",
                "Consejo del día: si el cliente dice «mañana le pago», anótelo en deudas y rece un Padre Nuestro.",
                "Consejo del día: tómese un tintico, respire hondo y piense: ¿esto me va a importar en cinco años? Si no, ¡a otra cosa, mariposa!",
                "Consejo del día: no se case con nadie, ni con el proveedor ni con el fiado. Cuentas claras, amistades largas.",
                "Consejo del día: el que no arriesga no gana, pero el que no hace inventario pierde hasta la camisa.",
                "Consejo del día: no se estrese, mijo. Lo que no se vendió hoy se vende mañana, y si no, hay promoción de «llévese dos».",
                "Consejo del día: ni tan calvo ni con dos pelucas. Ni regale todo ni cobre de más: el precio justo deja plata y deja volver al cliente.",
                "Consejo del día: el que mucho abarca poco aprieta. Un pedido a la vez, que el inventario no se ordena solo.",
                "Consejo del día: si el día salió malo, recuerde que los lunes pasan, las deudas se cobran y el sancocho del domingo no se cancela.",
                "Consejo del día: la vida es como un catálogo, parce: hay que mirarla completa y no quedarse solo con la primera página.",
                "Consejo del día: a quien le caiga mal lo que usted hace, que lo vaya mandando a freír espárragos. Usted siga vendiendo."
            ]
        },
        {
            palabras: ["personas estupidas", "persona estupida", "personaje estupida", "personajes estupidos", "personaje estupido", "gente estupida", "los estupidos", "las estupidas"],
            respuesta: [
                "Uy, ¿las personas estúpidas? Dicen que son muy patas, parce... pero yo soy una naranja, así que no tiro la primera piedra 🍊.",
                "Las personas estúpidas son muy patas, mijo. Pero tranquilo: lo que no se les puede explicar, se les anota en deudas y listo.",
                "Pienso lo mismo que de un cliente que no paga: que mejor no gastarle energía. Uno respira hondo, sonríe y sigue vendiendo."
            ]
        },
        {
            palabras: ["chiste", "hazme reir", "algo gracioso", "cuentame algo gracioso"],
            respuesta: [
                "Un cliente me dijo: «mañana le pago». Llevo tres meses esperando ese mañana 😅.",
                "¿Cuál es el colmo de una tienda por catálogo? Que le pidan algo y esté «agotado» en la página uno.",
                "¿Sabes cuál es el colmo de Naranjita? Que me digan que estoy muy verde... ¡y yo soy toda naranja!",
                "¿Por qué la naranja nunca se estresa? Porque siempre sabe sacarle el jugo a la vida 🍊."
            ]
        },
        {
            palabras: ["cuantos anos tienes", "que edad tienes", "cuando naciste", "cuantos anos tiene"],
            respuesta: [
                "Soy una naranjita joven: nací hace poquito, pero ya sé bastante de cuentas.",
                "Edad exacta no tengo, pero madurez de naranja sí 🍊. ¡Ya estoy en punto de jugo!"
            ]
        },
        {
            palabras: ["te quiero", "te amo", "eres genial", "eres la mejor", "eres bonita", "eres lo maximo", "eres muy buena"],
            respuesta: [
                "¡Ay, me sonrojé... y eso que ya soy naranja! Gracias, de verdad 🍊.",
                "Qué lindo, así da gusto trabajar. Yo también te aprecio, a mi manera de naranja.",
                "Uy, gracias, parce. Con ese cariño hasta el inventario se acomoda solo."
            ]
        },
        {
            palabras: ["calculadora", "hacer una cuenta", "hacer cuentas", "sabes sumar", "sabes calcular", "puedes sumar", "puedes calcular"],
            respuesta: "¡Claro! Soy buena para los números 🧮. Dime por ejemplo «cuánto es 25 mil por 3», «cuánto es 2 más 2» o «cuánto es el 10 por ciento de 50000»."
        },

        /* ---------- Saludos ---------- */
        {
            palabras: ["hola", "buenos dias", "buenas tardes", "buenas noches", "buenas", "hey", "saludos"],
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
        {
            palabras: ["que es una venta", "que es venta", "que es la venta", "que significa venta"],
            respuesta: "Una venta es el registro de lo que le vendes a un cliente: qué productos se llevó, cuántos, cuánto vale todo, cuánto pagó y cuánto queda debiendo. Se registra desde Ventas."
        },
        {
            palabras: ["que es un pedido", "que es pedido", "que es el pedido"],
            respuesta: "Un pedido es lo que le compras a un proveedor para llenar tu inventario. Cuando lo marcas como recibido, los productos entran al inventario."
        },
        {
            palabras: ["que es un abono", "que es abono"],
            respuesta: "Un abono es un pago parcial que hace el cliente sobre una deuda. Cada abono baja el saldo pendiente."
        },
        {
            palabras: ["que es una deuda", "que es deuda", "que es el fiado"],
            respuesta: "Una deuda es lo que un cliente todavía te debe de una venta que no pagó completa. Se va pagando con abonos."
        },
        {
            palabras: ["que es un producto", "que es producto"],
            respuesta: "Un producto es un artículo del catálogo que vendes, con su precio de compra, su precio de venta y cuántas unidades hay disponibles."
        },
        {
            palabras: ["que es el inventario", "que es inventario"],
            respuesta: "El inventario es la cuenta de cuántas unidades tienes de cada producto. Sube cuando recibes un pedido y baja cuando haces una venta."
        },

        /* ---------- Sobre el asistente ---------- */
        {
            palabras: ["que es mismary", "que es mis mary", "para que sirve mismary", "que es esto", "que gesto", "que es esta aplicacion", "que es esta app", "que es este sistema", "de que se trata", "que hace esta aplicacion", "para que sirve esto"],
            respuesta: "Esto es MisMary, una aplicación para gestión de ventas por catálogo. Sirve para registrar productos, inventario, proveedores, pedidos, clientes, ventas, deudas, abonos y reembolsos, y así tener un balance y cuentas claras."
        },
        {
            palabras: ["quien eres", "como te llamas", "que eres", "eres un robot", "eres real"],
            respuesta: "Soy Naranjita el asistente virtual de MisMary. Tengo respuestas preparadas para ayudarte a usar el sistema."
        },
        {
            palabras: ["que puedes hacer", "que haces", "para que sirves", "en que me ayudas"],
            respuesta: "Te oriento sobre productos, inventario, clientes, ventas, pedidos, proveedores, abonos, deudas, reembolsos y reportes. También hago cuentas, doy el consejo del día y cuento chistes 🍊."
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

    const SIN_RESPUESTA = "Lo siento, todavía no tengo una respuesta programada para esa pregunta. Puedes consultar las opciones del menú o comunicarte con un administrador de MisMary.";

    /* Si hay varias respuestas posibles, elige una al azar (sin repetir la anterior) */
    function elegir(opciones, bloque) {
        if (!Array.isArray(opciones)) return opciones;
        if (opciones.length === 1) return opciones[0];

        let elegida;
        do {
            elegida = opciones[Math.floor(Math.random() * opciones.length)];
        } while (elegida === bloque._ultima);

        bloque._ultima = elegida;
        return elegida;
    }

    /* Busca la primera respuesta cuya frase aparezca en lo que escribió la persona */
    function buscarRespuesta(texto) {
        const cuenta = calculadora(texto);
        if (cuenta) return cuenta;

        const consulta = normalizar(texto);

        for (const bloque of respuestas) {
            const coincide = bloque.palabras.some(function (frase) {
                return consulta.includes(normalizar(frase));
            });
            if (coincide) return elegir(bloque.respuesta, bloque);
        }

        return SIN_RESPUESTA;
    }

    /* Naranjita reacciona con una animación a saludos, despedidas y gracias.
       Devuelve true si ya reaccionó (para no animar dos veces). */
    function reaccionarAlUsuario(pregunta) {
        const saludos = ["hola", "buenos dias", "buenas tardes", "buenas noches", "buenas", "hey", "saludos"];
        const despedidas = ["adios", "hasta luego", "chao", "chau", "nos vemos", "hasta pronto", "bye", "me voy"];
        const gracias = ["gracias", "muchas gracias", "te agradezco", "mil gracias"];

        if (contiene(pregunta, saludos) || contiene(pregunta, despedidas)) {
            animar("Saludar");
            return true;
        }
        if (contiene(pregunta, gracias)) {
            animar("Brincar", 2);
            return true;
        }
        return false;
    }


    /* =================================================================
       6. CALCULADORA
       Entiende cosas como:
         "cuánto es 25 mil por 3"
         "cuánto es 2 más 2"
         "cuánto es el 10 por ciento de 50000"
       Devuelve el texto de la respuesta, o null si no era una cuenta.
       ================================================================= */
    function formatoNumero(n) {
        return Number(n.toFixed(4)).toLocaleString("es-CO", { maximumFractionDigits: 4 });
    }

    function calculadora(texto) {
        /* Limpieza (aquí NO quitamos los puntos ni las comas, son parte del número) */
        let t = texto.toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[¿?¡!]/g, "")
            .replace(/\s+/g, " ")
            .trim();

        /* ¿Empieza con "cuánto es", "calcula"...? Si sí, nos quedamos con lo que sigue.
           Si no, solo seguimos cuando todo el texto parece una cuenta (ej: "2+2"). */
        const disparador = /\b(cuanto (?:es|son|da|seria|sale|vale|me da)|calcula(?:me|r)?|resuelve|hazme la cuenta)\b/;
        const encontrado = t.match(disparador);

        if (encontrado) {
            t = t.slice(encontrado.index + encontrado[0].length).trim();
        } else if (!/^[\d\s.,+\-*\/x×÷()%]+$/.test(t)) {
            return null;
        }

        /* Paso 1: números escritos a la colombiana */
        while (/(\d)\.(\d{3})(?!\d)/.test(t)) {
            t = t.replace(/(\d)\.(\d{3})(?!\d)/, "$1$2");     /* 25.000  →  25000 */
        }
        t = t.replace(/(\d),(\d)/g, "$1.$2");                   /* 2,5     →  2.5   */
        t = t.replace(/(\d+(?:\.\d+)?)\s*millon(?:es)?/g, "($1*1000000)");   /* 2 millones → (2*1000000) */
        t = t.replace(/(\d+(?:\.\d+)?)\s*mil\b/g, "($1*1000)");              /* 25 mil     → (25*1000)   */

        /* Paso 2: porcentajes  ("10 por ciento de 50000" → "(10/100)*50000") */
        t = t.replace(/(\d+(?:\.\d+)?)\s*(?:por ciento|%)\s*de\s*/g, "($1/100)*");

        /* Paso 3: palabras → símbolos (primero dividir, luego multiplicar) */
        t = t
            .replace(/\bel\b/g, " ")
            .replace(/\bdividido (?:entre|por)\b|\bentre\b|\bsobre\b|÷/g, " / ")
            .replace(/\bmultiplicado por\b|\bveces\b|\bpor\b|\bx\b|×/g, " * ")
            .replace(/\bmas\b/g, " + ")
            .replace(/\bmenos\b/g, " - ");

        /* Paso 4: si quedó algo raro (letras, etc.), no era una cuenta */
        if (!/^[\d\s.+\-*\/()]+$/.test(t)) return null;
        if (!/[+\-*\/]/.test(t) || !/\d/.test(t)) return null;

        /* Paso 5: calcular (ya revisamos que solo hay números y símbolos) */
        let resultado;
        try {
            resultado = Function('"use strict"; return (' + t + ");")();
        } catch (e) {
            return null;
        }

        if (typeof resultado !== "number") return null;
        if (!isFinite(resultado)) {
            return "Dividir entre cero no se puede ni con calculadora de naranja 🍊. Prueba con otro número.";
        }

        const frases = ["Eso da", "Me da", "El resultado es"];
        const frase = frases[Math.floor(Math.random() * frases.length)];
        return frase + " " + formatoNumero(resultado) + " 🧮";
    }


    /* =================================================================
       7. MENSAJES DEL CHAT
       ================================================================= */
    function mostrarMensaje(texto, tipo) {
        const mensaje = document.createElement("div");
        mensaje.classList.add("asistente-mensaje", tipo);   /* tipo: "bot" o "usuario" */
        mensaje.textContent = texto;
        mensajes.appendChild(mensaje);
        mensajes.scrollTop = mensajes.scrollHeight;
    }

    /* Muestra la pregunta, busca la respuesta y la muestra después de un momentito */
    function enviarMensaje(texto) {
        const pregunta = texto.trim();
        if (!pregunta) return;

        mostrarMensaje(pregunta, "usuario");

        const respuesta = buscarRespuesta(pregunta);
        const yaReacciono = reaccionarAlUsuario(pregunta);

        window.setTimeout(function () {
            mostrarMensaje(respuesta, "bot");
            if (!yaReacciono) hablar(respuesta);
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


    /* =================================================================
       8. VOZ · HABLARLE A NARANJITA
       Se enciende con el botón del micrófono. Después, di "Naranjita"
       y tu orden. Ejemplos:
         "Naranjita, productos"          → abre Productos
         "Naranjita, registrar cliente"  → abre el formulario de cliente
         "Naranjita, modo oscuro"        → cambia el tema
         "Naranjita, atrás"              → vuelve a la página anterior
         "Naranjita, cerrar sesión"      → cierra la sesión
       Si dices una pregunta, la responde en el chat.
       Funciona en Chrome y Edge. Necesita internet y permiso de micrófono.
       ================================================================= */
    const Reconocimiento = window.SpeechRecognition || window.webkitSpeechRecognition;

    /* Secciones a las que puede llevarte (la clave debe existir en RUTAS_VOZ) */
    const SECCIONES = [
        { clave: "producto",  patron: /\bproductos?\b/,                          nombre: "Productos" },
        { clave: "cliente",   patron: /\bclientes?\b/,                           nombre: "Clientes" },
        { clave: "venta",     patron: /\bventas?\b/,                             nombre: "Ventas" },
        { clave: "pedido",    patron: /\bpedidos?\b/,                            nombre: "Pedidos" },
        { clave: "proveedor", patron: /\bproveedor(es)?\b/,                      nombre: "Proveedores" },
        { clave: "reembolso", patron: /\breembolsos?\b|\bdevoluci(on|ones)\b/,   nombre: "Reembolsos" },
        { clave: "reporte",   patron: /\b(reportes?|informes?)\b/,               nombre: "Reportes" },
        { clave: "grupo",     patron: /\bgrupos?\b|permisos?/,                   nombre: "Grupos" },
        { clave: "home",      patron: /\b(home|inicio|principal)\b/,             nombre: "Inicio" }
    ];

    /* Si la frase trae estas palabras, es una pregunta y va al chat, no es una orden */
    const NO_ES_COMANDO = /\b(que|como|cual|cuales|cuando|donde|por que|para que|pasa|funciona|funcionan|eliminar|elimino|borrar|anular|cancelar|estado|error|ayuda)\b/;
    const VERBO_CREAR = /\b(registrar|registra|crear|crea|nuevo|nueva|agregar|agrega|anadir|anade|solicitar|solicita)\b/;
    const ACTIVAR_COMANDO = /\b(activa|activar|activame|enciende|prende|inicia|empieza|comienza)\b.*(comando|voz|escuch)|\b(escuchame|dime|me escuchas|estas ahi)\b/;
    const DESACTIVAR_VOZ = /\b(desactiva|desactivar|apaga|apagar|deten|detener|deja de|para de|silencio)\b.*(comando|voz|escuch)/;

    let reconocimiento = null;      /* el "oído" del navegador */
    let escuchaActiva = false;      /* true = el micrófono está encendido */
    let modoComando = false;        /* true = la siguiente frase es una orden */
    let esperandoRegistro = 0;      /* momento en que dijo solo "registrar" */
    let temporizadorComando = null;
    let reinicio = null;
    let erroresSeguidos = 0;
    let inicioManual = false;       /* true si la persona pulsó el micrófono */
    let audioCtx = null;

    const placeholderOriginal = entrada.placeholder;
    const esBrave = !!(navigator.brave && navigator.brave.isBrave);

    /* ---------- Pitido corto para avisar que Naranjita te escuchó ---------- */
    function pitido(agudo) {
        try {
            audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
            const oscilador = audioCtx.createOscillator();
            const volumen = audioCtx.createGain();
            oscilador.frequency.value = agudo ? 880 : 440;
            volumen.gain.value = 0.05;
            oscilador.connect(volumen);
            volumen.connect(audioCtx.destination);
            oscilador.start();
            oscilador.stop(audioCtx.currentTime + 0.12);
        } catch (e) {}
    }

    /* ---------- Cambia el aspecto del botón del micrófono ---------- */
    function pintarEstado() {
        if (!microfono) return;
        microfono.classList.toggle("mic-activo", escuchaActiva);
        microfono.classList.toggle("mic-comando", escuchaActiva && modoComando);
        microfono.title = escuchaActiva
            ? "Escucha activa: di «Naranjita». Clic para apagar"
            : "Activar escucha por voz";
        entrada.placeholder = modoComando ? "Te escucho..." : placeholderOriginal;
    }

    function salirModoComando() {
        modoComando = false;
        window.clearTimeout(temporizadorComando);
        entrada.value = "";
        pintarEstado();
    }

    /* Naranjita oyó su nombre: ahora espera la orden (9 segundos) */
    function entrarModoComando() {
        modoComando = true;
        pintarEstado();
        pitido(true);
        abrirChat();
        mostrarMensaje("Te escucho. Dime qué necesitas.", "bot");
        window.clearTimeout(temporizadorComando);
        temporizadorComando = window.setTimeout(salirModoComando, 9000);
    }

    /* ---------- Ir a otra página ---------- */
    function irAPagina(ruta, mensaje) {
        mostrarMensaje(mensaje, "bot");
        animar("Brincar");
        try { sessionStorage.setItem("naranjitaAbierto", "1"); } catch (e) {}
        window.setTimeout(function () {
            window.location.href = ruta;
        }, 900);
    }

    /* ---------- Ejecutar una orden ----------
       Devuelve true si la frase era una orden y ya la ejecutó. */
    function ejecutarComando(texto) {
        const t = normalizar(texto);
        const palabras = t.split(/\s+/).filter(Boolean);

        /* Frases muy largas o con pinta de pregunta van al chat */
        if (!t || palabras.length > 10 || NO_ES_COMANDO.test(t)) return false;

        /* --- Modo oscuro / claro --- */
        const hablaDeTema = /\b(modo|tema)\b/.test(t) || /\boscuro\b/.test(t);
        if (hablaDeTema && /\b(oscuro|claro)\b/.test(t)) {
            const quiereOscuro = /oscuro/.test(t);
            const boton = document.getElementById("temaBtn");
            const actual = document.documentElement.getAttribute("data-theme");

            mostrarMensaje(texto, "usuario");
            if (boton && (quiereOscuro !== (actual === "dark"))) {
                boton.click();
            }
            mostrarMensaje(quiereOscuro ? "Listo, modo oscuro." : "Listo, modo claro.", "bot");
            animar("Brincar");
            return true;
        }

        /* --- Volver atrás --- */
        if (/\b(atras|volver|regresar)\b/.test(t)) {
            mostrarMensaje(texto, "usuario");
            mostrarMensaje("Volviendo a la página anterior.", "bot");
            try { sessionStorage.setItem("naranjitaAbierto", "1"); } catch (e) {}
            window.setTimeout(function () { window.history.back(); }, 700);
            return true;
        }

        /* --- Cerrar sesión --- */
        if (/cerrar sesion|salir del sistema/.test(t)) {
            const botonSalir = document.querySelector(".logout-btn");
            if (!botonSalir) return false;

            mostrarMensaje(texto, "usuario");
            mostrarMensaje("Cerrando sesión. ¡Hasta pronto!", "bot");
            animar("Saludar");
            window.setTimeout(function () { botonSalir.click(); }, 1200);
            return true;
        }

        /* --- Registrar algo nuevo / ir a una sección --- */
        const esperaba = esperandoRegistro && (Date.now() - esperandoRegistro) < 30000;
        const quiereCrear = VERBO_CREAR.test(t) || esperaba;

        /* Por seguridad, los usuarios no se crean por voz */
        if (quiereCrear && /\busuarios?\b/.test(t)) {
            esperandoRegistro = 0;
            mostrarMensaje(texto, "usuario");
            mostrarMensaje("Por seguridad, los usuarios no se pueden registrar por voz. Hazlo desde el sistema.", "bot");
            return true;
        }

        const seccion = SECCIONES.find(function (s) { return s.patron.test(t); });

        /* Dijo solo "registrar": le preguntamos qué */
        if (!seccion) {
            if (VERBO_CREAR.test(t)) {
                esperandoRegistro = Date.now();
                mostrarMensaje(texto, "usuario");
                mostrarMensaje("¿Qué quieres registrar? Puedo con cliente, producto, proveedor, venta, pedido o reembolso.", "bot");
                return true;
            }
            return false;
        }

        mostrarMensaje(texto, "usuario");

        /* "registrar cliente" → abre el formulario de nuevo cliente */
        if (quiereCrear) {
            esperandoRegistro = 0;
            const rutaNueva = RUTAS.registrar && RUTAS.registrar[seccion.clave];
            if (rutaNueva) {
                irAPagina(rutaNueva, "Abriendo el formulario de " + seccion.nombre.toLowerCase() + ".");
            } else {
                mostrarMensaje("No encontré la pantalla para registrar en " + seccion.nombre + ". Puedes entrar por el menú.", "bot");
            }
            return true;
        }

        /* "productos" → abre la lista de productos */
        let ruta = RUTAS[seccion.clave];

        /* Grupos solo existe en el menú del superusuario */
        if (seccion.clave === "grupo" && !document.querySelector('.sidebar-nav a[href="' + ruta + '"]')) {
            ruta = "";
        }

        if (ruta) {
            irAPagina(ruta, "Llevándote a " + seccion.nombre + ".");
        } else {
            mostrarMensaje("No tienes acceso a " + seccion.nombre + " o no encontré esa pantalla.", "bot");
        }
        return true;
    }

    /* Una orden: o la ejecuta como comando, o se la responde en el chat */
    function ejecutarOrden(texto) {
        if (DESACTIVAR_VOZ.test(normalizar(texto))) {
            apagarEscucha(true);
            return;
        }

        abrirChat();
        entrada.value = "";

        const frase = capitalizar(texto);
        if (!ejecutarComando(frase)) {
            enviarMensaje(frase);
        }
    }

    /* ---------- Cada frase que el navegador reconoce llega aquí ---------- */
    function alEscuchar(texto) {
        const t = normalizar(texto);
        if (!t) return;

        /* Lo que viene después de la palabra "Naranjita" */
        const sinClave = texto.replace(/^.*?\bnaranjit[ao]s?\b[\s,.:;!?¡¿-]*/i, "").trim();
        const dijoClave = /\bnaranjit[ao]s?\b/.test(t);

        /* Ya dijo "Naranjita" antes: esta frase es la orden */
        if (modoComando) {
            salirModoComando();
            ejecutarOrden(dijoClave ? sinClave : texto);
            return;
        }

        /* Todavía esperando que diga "Naranjita" */
        if (!dijoClave) return;

        const resto = normalizar(sinClave);

        if (DESACTIVAR_VOZ.test(resto)) {
            apagarEscucha(true);
        } else if (!resto || ACTIVAR_COMANDO.test(resto)) {
            entrarModoComando();          /* solo dijo "Naranjita" */
        } else {
            pitido(true);
            ejecutarOrden(sinClave);      /* dijo "Naranjita, productos" todo junto */
        }
    }

    /* ---------- Encender y apagar el micrófono ---------- */
    function crearReconocimiento() {
        const r = new Reconocimiento();
        r.lang = "es-CO";
        r.continuous = true;
        r.interimResults = true;
        r.maxAlternatives = 1;

        r.onresult = function (evento) {
            erroresSeguidos = 0;
            let provisional = "";

            for (let i = evento.resultIndex; i < evento.results.length; i++) {
                const parte = evento.results[i][0].transcript;
                if (evento.results[i].isFinal) {
                    alEscuchar(parte);
                } else {
                    provisional += parte;
                }
            }

            /* Mientras habla, muestra lo que va entendiendo */
            if (modoComando) entrada.value = provisional;
        };

        r.onerror = function (evento) {
            if (evento.error === "not-allowed" || evento.error === "service-not-allowed") {
                apagarEscucha(false);
                if (inicioManual) {
                    abrirChat();
                    mostrarMensaje("No tengo permiso para usar el micrófono. Actívalo en el candado de la barra de direcciones y vuelve a pulsar el micrófono.", "bot");
                }
            } else if (evento.error === "audio-capture") {
                apagarEscucha(false);
                abrirChat();
                mostrarMensaje("No encontré un micrófono conectado.", "bot");
            } else if (evento.error === "network") {
                erroresSeguidos += 1;
                if (esBrave || erroresSeguidos >= 5) {
                    apagarEscucha(false);
                    abrirChat();
                    mostrarMensaje(
                        esBrave
                            ? "Brave bloquea el servicio de voz de Google, por eso la voz no funciona en este navegador. Abre MisMary en Chrome o Edge para usarla."
                            : "No pude conectar con el servicio de voz del navegador. Revisa tu conexión (o usa Chrome o Edge) y vuelve a pulsar el micrófono.",
                        "bot"
                    );
                }
            }
        };

        /* Chrome corta la escucha cada cierto tiempo: aquí se vuelve a encender sola */
        r.onend = function () {
            if (escuchaActiva) {
                window.clearTimeout(reinicio);
                reinicio = window.setTimeout(arrancarReconocimiento, 400 + erroresSeguidos * 1500);
            }
        };

        return r;
    }

    function arrancarReconocimiento() {
        if (!escuchaActiva) return;
        try {
            reconocimiento = crearReconocimiento();
            reconocimiento.start();
        } catch (e) {}
    }

    function encenderEscucha(manual) {
        inicioManual = manual;
        escuchaActiva = true;
        try { localStorage.setItem("naranjitaVoz", "1"); } catch (e) {}
        pintarEstado();
        arrancarReconocimiento();

        if (manual) {
            abrirChat();
            pitido(true);
            mostrarMensaje("Escucha activada. Di «Naranjita» y después tu orden, por ejemplo: «Naranjita, productos» o «Naranjita, registrar cliente». También puedes decir solo «Naranjita» y esperar el aviso.", "bot");
        }
    }

    function apagarEscucha(avisar) {
        escuchaActiva = false;
        window.clearTimeout(reinicio);
        salirModoComando();
        try { localStorage.removeItem("naranjitaVoz"); } catch (e) {}
        try { if (reconocimiento) reconocimiento.abort(); } catch (e) {}
        pintarEstado();

        if (avisar) {
            pitido(false);
            mostrarMensaje("Escucha apagada. Pulsa el micrófono cuando quieras activarla de nuevo.", "bot");
        }
    }

    /* ---------- Botón del micrófono ---------- */
    if (microfono) {
        if (!Reconocimiento) {
            /* Firefox y otros navegadores no soportan la voz */
            microfono.style.display = "none";
        } else {
            microfono.addEventListener("click", function () {
                if (escuchaActiva) {
                    apagarEscucha(true);
                } else {
                    encenderEscucha(true);
                }
            });

            window.addEventListener("beforeunload", function () {
                try { if (reconocimiento) reconocimiento.abort(); } catch (e) {}
            });

            /* Si estaba activa en la página anterior, sigue activa en esta */
            try {
                if (localStorage.getItem("naranjitaVoz") === "1") {
                    encenderEscucha(false);
                }
            } catch (e) {}
        }
    }


    /* =================================================================
       MENSAJE DE BIENVENIDA
       ================================================================= */
    mostrarMensaje(
        "¡Hola! Soy Naranjita, el asistente virtual de MisMary. Puedes preguntarme sobre productos, inventario, ventas, pedidos y otras funciones de la tienda.",
        "bot"
    );

});