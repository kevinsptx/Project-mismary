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

    /* =====================================================
       NARANJITA 3D · animaciones
       Animaciones del modelo: Reposo, Saludar, Hablar,
       Brincar y Caminar.
       ===================================================== */
    const modelo = personaje.querySelector("model-viewer");
    const sinMovimiento = window.matchMedia &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let alTerminar = null;

    function puedeAnimar(nombre) {
        return !sinMovimiento &&
            modelo &&
            typeof modelo.play === "function" &&
            modelo.loaded &&
            Array.isArray(modelo.availableAnimations) &&
            modelo.availableAnimations.indexOf(nombre) !== -1;
    }

    const DURACIONES = { Saludar: 3, Hablar: 1.2, Brincar: 1, Caminar: 1 };
    let temporizadorAnimacion = null;

    /* Reposo: respira y mueve los brazos despacio, en bucle */
    function reposo() {
        alTerminar = null;
        window.clearTimeout(temporizadorAnimacion);
        if (!puedeAnimar("Reposo")) return;
        modelo.animationName = "Reposo";
        modelo.play({ repetitions: Infinity });
    }

    /* Hace una animación N veces y después vuelve a Reposo */
    function animar(nombre, repeticiones) {
        if (!puedeAnimar(nombre)) return;
        const veces = repeticiones || 1;
        alTerminar = reposo;
        modelo.animationName = nombre;
        modelo.play({ repetitions: veces });

        /* Seguro: si por algo no termina sola, vuelve a reposo igual */
        window.clearTimeout(temporizadorAnimacion);
        temporizadorAnimacion = window.setTimeout(function () {
            if (modelo.animationName === nombre) {
                reposo();
            }
        }, ((DURACIONES[nombre] || 2) * veces + 0.4) * 1000);
    }

    /* Saludos que hace sola: máximo 3 por pestaña (se cuentan aunque recargues) */
    const MAX_SALUDOS_AUTOMATICOS = 3;

    function saludoAutomatico() {
        if (ventana.classList.contains("abierto")) return;
        let hechos = 0;
        try { hechos = parseInt(sessionStorage.getItem("naranjitaSaludos") || "0", 10) || 0; } catch (e) {}
        if (hechos >= MAX_SALUDOS_AUTOMATICOS) return;
        try { sessionStorage.setItem("naranjitaSaludos", String(hechos + 1)); } catch (e) {}
        animar("Saludar");
    }

    if (modelo) {
        modelo.addEventListener("finished", function () {
            if (alTerminar) {
                const siguiente = alTerminar;
                alTerminar = null;
                siguiente();
            }
        });

        modelo.addEventListener("load", function () {
            reposo();
            /* Saluda un momento después de cargar la página (si aún no llegó al límite) */
            window.setTimeout(saludoAutomatico, 1500);
        });

        /* Si el modelo ya estaba cargado cuando corrió este script */
        if (modelo.loaded) {
            reposo();
        }
    }

    /* Mientras el chat está cerrado, saluda de vez en cuando (hasta el límite de arriba) */
    window.setInterval(saludoAutomatico, 40000);

    /* Habla (mueve los brazos y salta un poquito) según el largo del texto */
    function hablar(texto) {
        const milisegundos = Math.min(6000, Math.max(1500, texto.length * 50));
        animar("Hablar", Math.max(2, Math.round(milisegundos / 1200)));
    }

    /* =====================================================
       Ventana del chat
       ===================================================== */
    function abrirChat() {
        const yaEstabaAbierto = ventana.classList.contains("abierto");
        ventana.classList.add("abierto");

        if (invitacion) {
            invitacion.style.display = "none";
        }

        entrada.focus();

        if (!yaEstabaAbierto) {
            animar("Saludar");
        }
    }

    function cerrarChat() {
        ventana.classList.remove("abierto");
        reposo();
    }

    personaje.addEventListener("click", abrirChat);

    if (invitacion) {
        invitacion.addEventListener("click", abrirChat);
    }

    cerrar.addEventListener("click", cerrarChat);

    /* =====================================================
       Texto y reacciones a lo que dice la persona
       ===================================================== */
    function normalizar(texto) {
        return texto.toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[¿?¡!,.;:]/g, "")
            .trim();
    }

    const SALUDOS = ["hola", "buenos dias", "buenas tardes", "buenas noches", "buenas", "hey", "saludos"];
    const DESPEDIDAS = ["adios", "hasta luego", "chao", "chau", "nos vemos", "hasta pronto", "bye", "me voy"];
    const AGRADECIMIENTOS = ["gracias", "muchas gracias", "te agradezco", "mil gracias"];

    function contiene(texto, lista) {
        const t = " " + normalizar(texto) + " ";
        return lista.some(function (palabra) {
            return t.indexOf(" " + palabra + " ") !== -1;
        });
    }

    /* Devuelve true si hizo una reacción especial (saludo, despedida, gracias) */
    function reaccionarAlUsuario(pregunta) {
        if (contiene(pregunta, SALUDOS) || contiene(pregunta, DESPEDIDAS)) {
            animar("Saludar");
            return true;
        }

        if (contiene(pregunta, AGRADECIMIENTOS)) {
            animar("Brincar", 2);
            return true;
        }

        return false;
    }

    /* =====================================================
       Respuestas predeterminadas
       IMPORTANTE: gana la primera coincidencia.
       Las preguntas específicas van ANTES de las generales.
       ===================================================== */
    const respuestas = [

        /* ---------- Conversación (para que Naranjita se sienta más humana) ----------
           Si "respuesta" es una lista, Naranjita elige una al azar (sin repetir la anterior). */
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

    /* =====================================================
       Calculadora de Naranjita: "cuánto es 2 más 2"
       ===================================================== */
    function normalizarCalculo(texto) {
        return texto.toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[¿?¡!]/g, "")
            .replace(/\s+/g, " ")
            .trim();
    }

    function formatoNumero(n) {
        return Number(n.toFixed(4)).toLocaleString("es-CO", { maximumFractionDigits: 4 });
    }

    /* Devuelve el texto de la respuesta, o null si la frase no era una cuenta */
    function calculadora(texto) {
        let t = normalizarCalculo(texto);
        const disparador = /\b(cuanto (?:es|son|da|seria|sale|vale|me da)|calcula(?:me|r)?|resuelve|suma(?:me)?|resta(?:me)?|multiplica(?:me)?|divide(?:me)?|hazme la cuenta)\b/;
        const soloMatematica = /^[\d\s.,+\-*\/x×÷()%]+$/;
        const d = t.match(disparador);

        if (d) {
            t = t.slice(d.index + d[0].length).trim();
        } else if (!soloMatematica.test(t)) {
            return null;
        }

        const decir = function (cuenta, resultado) {
            const frases = ["Eso da", "Me da", "El resultado es"];
            const f = frases[Math.floor(Math.random() * frases.length)];
            return cuenta + " → " + f + " " + formatoNumero(resultado) + " 🧮";
        };

        /* "el 10 por ciento de 50000" */
        const porc = t.match(/^(?:el\s+)?(.+?)\s*(?:por ciento|%)\s*de\s+(.+)$/);
        if (porc) {
            const a = aNumero(porc[1]);
            const b = aNumero(porc[2]);
            if (!isNaN(a) && !isNaN(b)) {
                return decir(formatoNumero(a) + "% de " + formatoNumero(b), a * b / 100);
            }
        }

        t = t
            .replace(/\bmultiplicado por\b|\bmultiplicado\b|\bveces\b/g, " * ")
            .replace(/\bdividido (?:entre|por)\b|\bsobre\b|\bentre\b|÷/g, " / ")
            .replace(/\bmas\b/g, " + ")
            .replace(/\bmenos\b/g, " - ")
            .replace(/\bpor\b|\bx\b|×/g, " * ")
            .replace(/(\d)\s*-\s*(?=\d)/g, "$1 - ")
            .replace(/([+*\/])/g, " $1 ")
            .replace(/\s+/g, " ")
            .trim();

        const partes = t.split(/\s+([+\-*\/])\s+/);
        if (partes.length < 3) return null;

        const nums = [];
        const ops = [];
        partes.forEach(function (p, i) {
            if (i % 2 === 0) nums.push(aNumero(p));
            else ops.push(p);
        });
        if (nums.some(function (n) { return isNaN(n); })) return null;

        /* Primero multiplicar y dividir, después sumar y restar */
        const valores = [nums[0]];
        const sumas = [];
        for (let i = 0; i < ops.length; i++) {
            const b = nums[i + 1];
            if (ops[i] === "*") {
                valores[valores.length - 1] *= b;
            } else if (ops[i] === "/") {
                if (b === 0) return "Dividir entre cero no se puede ni con calculadora de naranja 🍊. Prueba con otro número.";
                valores[valores.length - 1] /= b;
            } else {
                sumas.push(ops[i]);
                valores.push(b);
            }
        }
        let resultado = valores[0];
        sumas.forEach(function (op, i) {
            resultado = op === "+" ? resultado + valores[i + 1] : resultado - valores[i + 1];
        });

        const simbolo = { "*": "×", "/": "÷", "+": "+", "-": "−" };
        const cuenta = nums.map(formatoNumero).reduce(function (acc, n, i) {
            return acc + " " + simbolo[ops[i - 1]] + " " + n;
        });
        return decir(cuenta, resultado);
    }

    /* Elige una respuesta al azar cuando hay varias, sin repetir la anterior */
    function elegir(opciones, elemento) {
        if (!Array.isArray(opciones)) return opciones;
        if (opciones.length === 1) return opciones[0];
        let r;
        do {
            r = opciones[Math.floor(Math.random() * opciones.length)];
        } while (r === elemento._ultima);
        elemento._ultima = r;
        return r;
    }

    function buscarRespuesta(texto) {
        const cuenta = calculadora(texto);
        if (cuenta) {
            return cuenta;
        }

        const consulta = normalizar(texto);

        for (const elemento of respuestas) {
            const coincide = elemento.palabras.some(function (palabra) {
                const clave = normalizar(palabra);
                return consulta === clave || consulta.includes(clave);
            });

            if (coincide) {
                return elegir(elemento.respuesta, elemento);
            }
        }

        return SIN_RESPUESTA;
    }

    /* =====================================================
       Mensajes
       ===================================================== */
    function mostrarMensaje(texto, tipo) {
        const mensaje = document.createElement("div");
        mensaje.classList.add("asistente-mensaje", tipo);
        mensaje.textContent = texto;
        mensajes.appendChild(mensaje);
        mensajes.scrollTop = mensajes.scrollHeight;
    }

    function enviarMensaje(texto) {
        const pregunta = texto.trim();

        if (!pregunta) return;

        mostrarMensaje(pregunta, "usuario");

        const respuesta = buscarRespuesta(pregunta);
        const reaccion = reaccionarAlUsuario(pregunta);

        window.setTimeout(function () {
            mostrarMensaje(respuesta, "bot");

            /* Si ya saludó o brincó, deja que termine; si no, habla la respuesta */
            if (!reaccion) {
                hablar(respuesta);
            }
        }, 350);

        entrada.value = "";
        entrada.focus();
    }

    /* =====================================================
       VOZ · hablarle a Naranjita (manos libres)
       Se enciende una vez con el botón del micrófono y después
       responde a la palabra clave "Naranjita".
       Funciona en Chrome y Edge. Necesita internet y permiso
       del micrófono.
       Las rutas llegan desde base.html en window.RUTAS_VOZ.
       ===================================================== */
    const RUTAS = window.RUTAS_VOZ || { registrar: {} };
    const microfono = document.getElementById("asistente-microfono");
    const Reconocimiento = window.SpeechRecognition || window.webkitSpeechRecognition;

    const ENTIDADES = [
        { clave: "producto",  patron: /\bproductos?\b/,          nombre: "Productos" },
        { clave: "cliente",   patron: /\bclientes?\b/,           nombre: "Clientes" },
        { clave: "venta",     patron: /\bventas?\b/,             nombre: "Ventas" },
        { clave: "pedido",    patron: /\bpedidos?\b/,            nombre: "Pedidos" },
        { clave: "proveedor", patron: /\bproveedor(es)?\b/,      nombre: "Proveedores" },
        { clave: "reembolso", patron: /\breembolsos?\b|\bdevoluci(on|ones)\b/, nombre: "Reembolsos" },
        { clave: "reporte",   patron: /\b(reportes?|informes?)\b/, nombre: "Reportes" },
        { clave: "grupo",     patron: /\bgrupos?\b|permisos?/,   nombre: "Grupos" },
        { clave: "home",      patron: /\b(home|inicio|principal)\b/, nombre: "Inicio" }
    ];

    /* Si la frase parece una pregunta, se la pasamos al chat y no a los comandos */
    const NO_ES_COMANDO = /\b(que|como|cual|cuales|cuando|donde|por que|para que|pasa|funciona|funcionan|eliminar|elimino|borrar|anular|cancelar|estado|error|ayuda)\b/;
    let esperandoRegistro = 0;   /* momento en que dijo solo "registrar" */
    const VERBO_CREAR = /\b(registrar|registra|crear|crea|nuevo|nueva|agregar|agrega|anadir|anade|solicitar|solicita)\b/;

    /* ---------- Formularios por voz ---------- */
    const ALIAS_CAMPOS = [
        { alias: ["nombre completo", "nombre"],                               claves: ["nombre"],                                        numerico: false },
        { alias: ["apellido", "apellidos"],                                   claves: ["apellido"],                                      numerico: false },
        { alias: ["numero de telefono", "numero de celular", "telefono", "celular", "movil"], claves: ["telefono", "celular", "movil", "tel"], numerico: true },
        { alias: ["correo electronico", "correo", "email", "mail"],           claves: ["correo", "email", "mail"],                       numerico: false },
        { alias: ["direccion"],                                               claves: ["direccion", "address"],                          numerico: false },
        { alias: ["cedula", "documento", "nit", "identificacion"],            claves: ["cedula", "documento", "nit", "identificacion"],  numerico: true },
        { alias: ["precio", "valor"],                                         claves: ["precio", "valor", "price"],                      numerico: true, cifra: true },
        { alias: ["cantidad", "unidades"],                                    claves: ["cantidad", "stock", "unidades"],                 numerico: true, cifra: true },
        { alias: ["fecha"],                                                   claves: ["fecha"],                                         numerico: false, fecha: true },
        { alias: ["descripcion"],                                             claves: ["descripcion", "detalle"],                        numerico: false },
        { alias: ["ciudad"],                                                  claves: ["ciudad"],                                        numerico: false },
        { alias: ["barrio"],                                                  claves: ["barrio"],                                        numerico: false },
        /* Listas desplegables: si el formulario no las tiene, la frase sigue su camino normal */
        { alias: ["cliente"],                                                 claves: ["cliente"],                                       numerico: false, suave: true },
        { alias: ["producto"],                                                claves: ["producto"],                                      numerico: false, suave: true },
        { alias: ["proveedor"],                                               claves: ["proveedor"],                                     numerico: false, suave: true },
        { alias: ["categoria"],                                               claves: ["categoria"],                                     numerico: false, suave: true },
        { alias: ["metodo de pago", "forma de pago"],                         claves: ["pago", "metodo"],                                numerico: false, suave: true },
        { alias: ["estado"],                                                  claves: ["estado"],                                        numerico: false, suave: true }
    ];

    const TIPOS_NO_LLENABLES = ["hidden", "submit", "button", "checkbox", "radio", "file", "password", "reset", "image"];

    function titulo(texto) {
        return texto.toLowerCase().replace(/(^|\s)([a-záéíóúüñ])/gu, function (_, e, l) {
            return e + l.toUpperCase();
        });
    }

    function camposDelFormulario() {
        const contenido = document.querySelector("main.contenido");
        if (!contenido) return [];

        const valido = function (c) {
            return TIPOS_NO_LLENABLES.indexOf(c.type) === -1 &&
                !c.disabled && !c.readOnly &&
                !c.closest("#asistente-formulario") && !c.closest(".logout-form") &&
                !c.closest("form[method='get']");   /* buscadores y filtros no cuentan */
        };

        let campos = Array.from(contenido.querySelectorAll("form input, form select, form textarea")).filter(valido);
        if (campos.length < 2) {
            /* Pantallas armadas sin la etiqueta <form> */
            campos = Array.from(contenido.querySelectorAll("input, select, textarea")).filter(valido);
        }
        return campos;
    }

    function listaDeCampos(campos) {
        const vistos = [];
        campos.forEach(function (c) {
            const nombre = etiquetaDe(c) || c.placeholder || c.name || c.id;
            if (nombre && vistos.indexOf(nombre) === -1) vistos.push(nombre);
        });
        return vistos.slice(0, 14).join(", ");
    }

    function valorVisible(campo) {
        if (campo.tagName === "SELECT" && campo.selectedIndex >= 0) {
            return campo.options[campo.selectedIndex].text.trim();
        }
        return campo.value;
    }

    function etiquetaDe(campo) {
        let etiqueta = "";
        if (campo.id) {
            const l = document.querySelector('label[for="' + campo.id + '"]');
            if (l) etiqueta = l.textContent;
        }
        if (!etiqueta) {
            const l = campo.closest("label");
            if (l) etiqueta = l.textContent;
        }
        return etiqueta.replace(/[*:]/g, "").trim();
    }

    function textoDelCampo(campo) {
        return normalizar([campo.name, campo.id, campo.placeholder, etiquetaDe(campo)].join(" "));
    }

    function buscarCampo(campos, claves) {
        return campos.find(function (c) {
            const t = textoDelCampo(c);
            return claves.some(function (k) { return t.indexOf(k) !== -1; });
        });
    }

    let ambiguedad = [];   /* opciones que empatan cuando la lista tiene varias parecidas */

    function rellenar(campo, valor, numerico) {
        ambiguedad = [];
        if (campo.tagName === "SELECT") {
            const buscado = normalizar(valor);
            let palabrasValor = buscado.split(/\s+/).filter(Boolean);
            const largas = palabrasValor.filter(function (p) { return p.length > 2; });
            if (largas.length) palabrasValor = largas;
            const necesarias = palabrasValor.length <= 3 ? palabrasValor.length : Math.ceil(palabrasValor.length * 0.75);
            let mejores = [];
            let mejorPuntos = 0;

            Array.from(campo.options).forEach(function (o) {
                const ot = normalizar(o.text);
                if (o.value === "" || !ot) return;
                const puntos = palabrasValor.filter(function (p) { return ot.indexOf(p) !== -1; }).length;
                if (puntos < necesarias) return;
                const total = puntos + (ot === buscado ? 100 : 0);
                if (total > mejorPuntos) {
                    mejorPuntos = total;
                    mejores = [o];
                } else if (total === mejorPuntos) {
                    mejores.push(o);
                }
            });

            if (!mejores.length) return false;
            if (mejores.length > 1) {
                ambiguedad = mejores.slice(0, 5).map(function (o) { return o.text.trim(); });
                return false;
            }
            campo.value = mejores[0].value;
        } else if (numerico) {
            let v = valor.replace(/\s/g, "");
            if (/^\d{1,3}(\.\d{3})+(,\d+)?$/.test(v)) {
                v = v.replace(/\./g, "").replace(",", ".");
            } else {
                v = v.replace(/,/g, ".");
            }
            campo.value = v.replace(/[^\d.-]/g, "");
        } else {
            campo.value = valor;
        }
        campo.dispatchEvent(new Event("input", { bubbles: true }));
        campo.dispatchEvent(new Event("change", { bubbles: true }));
        try {
            campo.scrollIntoView({ block: "center", behavior: "smooth" });
            const antes = campo.style.boxShadow;
            campo.style.boxShadow = "0 0 0 4px rgba(255, 107, 53, 0.55)";
            window.setTimeout(function () { campo.style.boxShadow = antes; }, 1600);
        } catch (e) {}
        return true;
    }

    function camposFaltantes() {
        return camposDelFormulario()
            .filter(function (c) { return c.required && !c.value; })
            .map(function (c) { return etiquetaDe(c) || c.name; })
            .filter(Boolean);
    }

    function hayObligatorios() {
        return camposDelFormulario().some(function (c) { return c.required; });
    }

    function resumenFormulario() {
        if (formularioConLineas()) {
            return "Cuando termines, di «registrar venta».";
        }
        const faltan = camposFaltantes();
        if (faltan.length) {
            return "Faltan: " + faltan.join(", ") + ". Dime por ejemplo «" + (faltan[0].toLowerCase() || "dato") + " y el valor».";
        }
        if (!hayObligatorios()) {
            return "Cuando termines, di «guardar».";
        }
        return "Si no agregas más datos, lo registro en 5 segundos. Di «cancelar» para detenerlo o «guardar» para hacerlo ya.";
    }

    /* ----- Guardado automático (con cuenta regresiva para poder cancelar) ----- */
    let temporizadorGuardado = null;
    let guardadoPendiente = false;

    function cancelarGuardadoProgramado() {
        window.clearTimeout(temporizadorGuardado);
        const habia = guardadoPendiente;
        guardadoPendiente = false;
        return habia;
    }

    function guardarAhora() {
        cancelarGuardadoProgramado();
        const campos = camposDelFormulario();
        if (campos.length < 2) return;
        const f = campos[0].closest("form");

        if (!f) {
            const boton = Array.from(document.querySelectorAll("main.contenido button, main.contenido input[type='submit']"))
                .find(function (b) { return /guardar|registrar|crear|enviar|finalizar|confirmar/i.test(b.textContent || b.value || ""); });
            if (boton) {
                try {
                    sessionStorage.setItem("naranjitaAbierto", "1");
                    sessionStorage.setItem("naranjitaGuardando", "1");
                } catch (e) {}
                boton.click();
            } else {
                mostrarMensaje("No encontré el botón para guardar. Púlsalo tú.", "bot");
            }
            return;
        }

        if (f.checkValidity && !f.checkValidity()) {
            f.reportValidity();
            const malo = f.querySelector(":invalid");
            const nombre = malo ? (etiquetaDe(malo) || (malo.classList.contains("sel-producto") ? "Producto" : malo.name)) : "";
            mostrarMensaje("Todavía no puedo registrarlo" + (nombre ? ": revisa «" + nombre + "»" : "") +
                (malo && malo.validationMessage ? " (" + malo.validationMessage + ")" : "") + ".", "bot");
            return;
        }

        try {
            sessionStorage.setItem("naranjitaAbierto", "1");
            sessionStorage.setItem("naranjitaGuardando", "1");
        } catch (e) {}
        if (f.requestSubmit) {
            f.requestSubmit();
        } else {
            f.submit();
        }
    }

    /* Si ya no falta nada, lo registra a los 5 segundos de silencio */
    function programarGuardado() {
        cancelarGuardadoProgramado();
        /* Sin campos obligatorios no se guarda solo: se espera la orden "guardar" */
        if (formularioConLineas()) return;   /* la venta solo se guarda cuando lo pides */
        if (camposDelFormulario().length < 2 || !hayObligatorios() || camposFaltantes().length) return;
        guardadoPendiente = true;
        temporizadorGuardado = window.setTimeout(function () {
            guardadoPendiente = false;
            mostrarMensaje("Registrando...", "bot");
            animar("Brincar");
            guardarAhora();
        }, 5000);
    }

    /* Si la persona empieza a escribir con el teclado, no se guarda solo */
    document.addEventListener("input", function (evento) {
        if (guardadoPendiente && evento.isTrusted) {
            cancelarGuardadoProgramado();
            mostrarMensaje("Vi que estás escribiendo, así que no lo guardo solo. Di «guardar» cuando termines.", "bot");
        }
    });

    /* Mientras se llena un formulario no hace falta repetir "Naranjita" cada vez */
    function rearmarModoFormulario() {
        if (!escuchaActiva) return;
        modoComando = true;
        pintarEstado();
        window.clearTimeout(temporizadorComando);
        temporizadorComando = window.setTimeout(salirModoComando, 45000);
    }

    /* ---------- Números y fechas dichos en voz ---------- */
    const NUM_BASE = {
        cero: 0, un: 1, uno: 1, una: 1, dos: 2, tres: 3, cuatro: 4, cinco: 5, seis: 6, siete: 7, ocho: 8, nueve: 9,
        diez: 10, once: 11, doce: 12, trece: 13, catorce: 14, quince: 15, dieciseis: 16, diecisiete: 17,
        dieciocho: 18, diecinueve: 19, veinte: 20, veintiun: 21, veintiuno: 21, veintiuna: 21, veintidos: 22,
        veintitres: 23, veinticuatro: 24, veinticinco: 25, veintiseis: 26, veintisiete: 27, veintiocho: 28,
        veintinueve: 29, treinta: 30, cuarenta: 40, cincuenta: 50, sesenta: 60, setenta: 70, ochenta: 80,
        noventa: 90, cien: 100, ciento: 100, doscientos: 200, doscientas: 200, trescientos: 300, trescientas: 300,
        cuatrocientos: 400, cuatrocientas: 400, quinientos: 500, quinientas: 500, seiscientos: 600,
        seiscientas: 600, setecientos: 700, setecientas: 700, ochocientos: 800, ochocientas: 800,
        novecientos: 900, novecientas: 900
    };

    function palabrasANumero(t) {
        const palabras = t.split(/\s+/).filter(function (w) { return w && w !== "y" && w !== "de" && w !== "pesos" && w !== "peso"; });
        let total = 0;
        let actual = 0;
        let reconocidas = 0;
        for (const w of palabras) {
            if (Object.prototype.hasOwnProperty.call(NUM_BASE, w)) {
                actual += NUM_BASE[w];
                reconocidas++;
            } else if (w === "mil") {
                total += (actual || 1) * 1000;
                actual = 0;
                reconocidas++;
            } else if (w === "millon" || w === "millones") {
                total += (actual || 1) * 1000000;
                actual = 0;
                reconocidas++;
            } else {
                return NaN;
            }
        }
        return reconocidas ? total + actual : NaN;
    }

    /* "50 mil", "50.000", "cincuenta mil", "3" → número */
    function aNumero(texto) {
        const t = normalizar(texto).replace(/\$/g, "").replace(/\bpesos?\b/g, "").trim();
        const m = t.match(/^(\d{1,3}(?:[.\s]\d{3})+|\d+)(?:,(\d+))?\s*(mil|millon|millones)?$/);
        if (m) {
            let n = parseInt(m[1].replace(/[.\s]/g, ""), 10);
            if (m[2]) n = parseFloat(n + "." + m[2]);
            if (m[3] === "mil") n *= 1000;
            else if (m[3]) n *= 1000000;
            return n;
        }
        return palabrasANumero(t);
    }

    const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];

    /* "hoy", "ayer", "15 de noviembre" → "2026-11-15" */
    function aFecha(texto) {
        const t = normalizar(texto);
        const hoy = new Date();
        let d = null;
        if (/\bhoy\b/.test(t)) {
            d = new Date(hoy);
        } else if (/\banteayer\b/.test(t)) {
            d = new Date(hoy);
            d.setDate(d.getDate() - 2);
        } else if (/\bayer\b/.test(t)) {
            d = new Date(hoy);
            d.setDate(d.getDate() - 1);
        } else {
            const m = t.match(/(\d{1,2})\s*(?:de\s+)?(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)(?:\s*(?:de\s+)?(\d{4}))?/);
            if (m) {
                d = new Date(m[3] ? parseInt(m[3], 10) : hoy.getFullYear(), MESES.indexOf(m[2]), parseInt(m[1], 10));
            }
        }
        if (!d || isNaN(d.getTime())) return "";
        const dos = function (n) { return String(n).padStart(2, "0"); };
        return d.getFullYear() + "-" + dos(d.getMonth() + 1) + "-" + dos(d.getDate());
    }

    /* ---------- Formularios con líneas de productos (la venta) ---------- */
    let filaActual = null;

    function formularioConLineas() {
        return !!document.querySelector("main.contenido #lista-productos, main.contenido .fila-producto");
    }

    function filasProducto() {
        return Array.from(document.querySelectorAll("main.contenido .fila-producto"));
    }

    function textoDe(id) {
        const e = document.getElementById(id);
        return e ? e.textContent.trim() : "";
    }

    function opcionElegida(sel) {
        return sel && sel.selectedIndex >= 0 ? sel.options[sel.selectedIndex] : null;
    }

    function nombreDeLinea(fila) {
        const o = opcionElegida(fila.querySelector(".sel-producto"));
        return o && o.value ? o.text.replace(/\s+/g, " ").trim() : "";
    }

    function filaLibre() {
        return filasProducto().find(function (f) { return !f.querySelector(".sel-producto").value; });
    }

    /* Devuelve una línea vacía (la crea con "+ Agregar producto" si hace falta) */
    function lineaNueva() {
        let fila = filaLibre();
        if (!fila) {
            const boton = document.getElementById("btn-agregar");
            if (boton) boton.click();
            fila = filaLibre();
        }
        return fila;
    }

    function quitarLinea(fila) {
        const quitar = fila && fila.querySelector(".btn-quitar");
        if (quitar && filasProducto().length > 1) {
            quitar.click();
            return true;
        }
        return false;
    }

    function fijarCantidad(fila, n) {
        const campo = fila.querySelector(".inp-cantidad");
        const opcion = opcionElegida(fila.querySelector(".sel-producto"));
        const stock = opcion ? parseInt(opcion.dataset.stock, 10) : NaN;
        let aviso = "";
        if (!isNaN(stock) && n > stock) {
            aviso = " Solo hay " + stock + " disponibles, así que puse " + stock + ".";
            n = stock;
        }
        if (n < 1) n = 1;
        rellenar(campo, String(n), true);
        return aviso;
    }

    function anadirProducto(nombre, cantidad) {
        const antes = filasProducto().length;
        const fila = lineaNueva();
        if (!fila) return { ok: false, texto: "No pude agregar otra línea de producto." };
        const creada = filasProducto().length > antes;
        const sel = fila.querySelector(".sel-producto");

        if (!rellenar(sel, nombre, false)) {
            if (creada) quitarLinea(fila);
            if (ambiguedad.length) {
                return { ok: false, texto: "Hay varios productos que coinciden con «" + nombre + "»: " + ambiguedad.map(function (o) { return o.replace(/\s*-\s*\$.*$/, ""); }).join(", ") + ". Dime el nombre completo." };
            }
            const algunos = Array.from(sel.options)
                .filter(function (o) { return o.value; })
                .slice(0, 6)
                .map(function (o) { return o.text.replace(/\s+/g, " ").replace(/\s*-\s*\$.*$/, "").trim(); })
                .join(", ");
            return { ok: false, texto: "No encontré «" + nombre + "» en los productos. Algunos son: " + algunos + "." };
        }

        /* Si ese producto ya estaba en la venta, se suma a su línea en vez de repetirla */
        const repetida = filasProducto().find(function (f) {
            return f !== fila && f.querySelector(".sel-producto").value === sel.value;
        });
        if (repetida) {
            const actual = parseInt(repetida.querySelector(".inp-cantidad").value, 10) || 0;
            const extra = cantidad || 1;
            quitarLinea(fila);
            const aviso = fijarCantidad(repetida, actual + extra);
            filaActual = repetida;
            return { ok: true, texto: nombreDeLinea(repetida).replace(/\s*-\s*\$.*$/, "") + " ya estaba, ahora son " +
                repetida.querySelector(".inp-cantidad").value + "." + aviso };
        }

        filaActual = fila;
        const aviso = cantidad ? fijarCantidad(fila, cantidad) : "";
        const n = fila.querySelector(".inp-cantidad").value;
        return { ok: true, texto: nombreDeLinea(fila).replace(/\s*-\s*\$.*$/, "") + " × " + n + "." + aviso };
    }

    /* "agua micelar cantidad 2", "crema 3 unidades", "2 unidades de labial", "labial 2" */
    function intentarProducto(texto) {
        const t = texto.trim();
        let m = t.match(/^(\S+)\s+unidades?\s+de\s+(.+)$/);
        if (m && !isNaN(aNumero(m[1]))) return anadirProducto(m[2], aNumero(m[1]));

        m = t.match(/^(.*?)\s+(?:cantidad|por|x)\s+(.+)$/);
        if (m && !isNaN(aNumero(m[2]))) return anadirProducto(m[1], aNumero(m[2]));

        m = t.match(/^(.*?)\s+(\S+)\s+unidades?$/);
        if (m && !isNaN(aNumero(m[2]))) return anadirProducto(m[1], aNumero(m[2]));

        m = t.match(/^(.*\D)\s+(\d{1,3})$/);
        if (m) {
            const r = anadirProducto(m[1], parseInt(m[2], 10));
            if (r.ok) return r;
        }
        return anadirProducto(t, 0);
    }

    function resumenDeVenta() {
        const lineas = filasProducto()
            .filter(function (f) { return nombreDeLinea(f); })
            .map(function (f) { return nombreDeLinea(f).replace(/\s*-\s*\$.*$/, "") + " × " + f.querySelector(".inp-cantidad").value; });
        const cliente = document.getElementById("cliente");
        const quien = cliente && cliente.value ? cliente.options[cliente.selectedIndex].text.trim() : "sin cliente";
        return "Venta de " + quien + ": " + (lineas.length ? lineas.join("; ") : "sin productos") +
            ". Total " + textoDe("total") + ". Falta por pagar " + textoDe("falta") + ".";
    }

    /* Devuelve true si la frase era para la venta y ya la ejecutó */
    function ejecutarEnVentas(texto, t) {
        const pn = t.split(/\s+/).filter(Boolean);
        const cierre = " Cuando termines, di «registrar venta».";

        /* Nueva línea de producto */
        if (/^(?:(?:otro|nuevo|siguiente|agregar|agrega|anadir|anade)(?: un)? producto|producto)$/.test(t)) {
            mostrarMensaje(texto, "usuario");
            if (lineaNueva()) {
                mostrarMensaje("Línea nueva lista. Dime el producto, por ejemplo «agua micelar cantidad 2».", "bot");
            } else {
                mostrarMensaje("No pude agregar otra línea.", "bot");
            }
            return true;
        }

        /* Quitar el último producto */
        if (/^(?:quitar|quita|borrar|borra|eliminar|elimina)(?: el| la)?(?: ultimo| ultima)? (?:producto|linea)$/.test(t)) {
            mostrarMensaje(texto, "usuario");
            const filas = filasProducto();
            if (quitarLinea(filas[filas.length - 1])) {
                filaActual = null;
                mostrarMensaje("Quité la última línea. Total " + textoDe("total") + ".", "bot");
            } else {
                mostrarMensaje("Solo queda una línea, no la puedo quitar.", "bot");
            }
            return true;
        }

        /* Resumen */
        if (/\b(resumen|leeme|como va|como vamos|que llevo|que llevamos)\b/.test(t)) {
            mostrarMensaje(texto, "usuario");
            mostrarMensaje(resumenDeVenta(), "bot");
            return true;
        }

        /* Pago del cliente: "abono 50000", "pagó 50 mil", "primera cuota 30000" */
        const pago = t.match(/^(?:el cliente )?(?:ya )?(?:valor pagado|pagado|pago inicial|pago|abono inicial|abono|primera cuota|cuota inicial|cuota)(?: es| fue| de| son| del cliente)?\s+(.+)$/);
        if (pago) {
            mostrarMensaje(texto, "usuario");
            const n = aNumero(pago[1]);
            const campo = document.getElementById("valor_pagado_visible");
            if (isNaN(n) || !campo) {
                mostrarMensaje("No entendí el valor. Dime por ejemplo «abono 50000» o «abono 50 mil».", "bot");
                return true;
            }
            rellenar(campo, String(Math.round(n)), true);
            const aviso = campo.validationMessage ? " Ojo: " + campo.validationMessage : "";
            mostrarMensaje("Anoté un pago de $ " + String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ".") +
                ". Total " + textoDe("total") + ". Falta por pagar " + textoDe("falta") + "." + aviso + cierre, "bot");
            return true;
        }

        /* Cantidad de la última línea */
        const cant = t.match(/^(?:cantidad|unidades)\s+(.+)$/);
        if (cant) {
            mostrarMensaje(texto, "usuario");
            const n = aNumero(cant[1]);
            let fila = filaActual && document.body.contains(filaActual) ? filaActual : null;
            if (!fila) {
                const conProducto = filasProducto().filter(function (f) { return nombreDeLinea(f); });
                fila = conProducto[conProducto.length - 1];
            }
            if (isNaN(n)) {
                mostrarMensaje("No entendí la cantidad. Dime por ejemplo «cantidad 3».", "bot");
            } else if (!fila) {
                mostrarMensaje("Primero dime el producto, por ejemplo «producto agua micelar».", "bot");
            } else {
                const aviso = fijarCantidad(fila, n);
                mostrarMensaje(nombreDeLinea(fila).replace(/\s*-\s*\$.*$/, "") + " × " + fila.querySelector(".inp-cantidad").value + "." + aviso +
                    " Total " + textoDe("total") + "." + cierre, "bot");
            }
            return true;
        }

        /* Productos: "producto agua micelar cantidad 2", "agrega base líquida y contorno de ojos" */
        const prod = t.match(/^(?:producto|agrega|agregar|anade|anadir|lleva|llevar|pon|poner)\s+(.+)$/);
        if (prod && pn.length >= 2) {
            mostrarMensaje(texto, "usuario");
            const resto = prod[1];
            let resultados = [];
            let primero = intentarProducto(resto);

            if (primero.ok) {
                resultados = [primero];
            } else if (/(,|\by\b|\bmas\b)/.test(resto)) {
                const partes = resto.split(/\s*(?:,|\by\b|\bmas\b)\s*/).filter(Boolean);
                resultados = partes.length > 1 ? partes.map(intentarProducto) : [primero];
            } else {
                resultados = [primero];
            }

            const buenos = resultados.filter(function (r) { return r.ok; }).map(function (r) { return r.texto; });
            const malos = resultados.filter(function (r) { return !r.ok; }).map(function (r) { return r.texto; });
            let mensaje = "";
            if (buenos.length) mensaje += "Agregué: " + buenos.join(" ") + " Total " + textoDe("total") + ".";
            if (malos.length) mensaje += (mensaje ? " " : "") + malos.join(" ");
            if (buenos.length) {
                animar("Brincar");
                mensaje += " Sigue con otro producto, el «abono» o «registrar venta».";
            }
            mostrarMensaje(mensaje, "bot");
            return true;
        }

        return false;
    }

    /* Devuelve true si la frase era para el formulario abierto y ya la ejecutó */
    function ejecutarEnFormulario(texto) {
        const campos = camposDelFormulario();
        if (campos.length < 2) return false;

        const t = normalizar(texto);
        const pn = t.split(/\s+/).filter(Boolean);

        /* Guardar ya: "guardar", "registrar venta", "finalizar"... */
        const textoBoton = Array.from(document.querySelectorAll("main.contenido button, main.contenido input[type='submit']"))
            .map(function (b) { return normalizar(b.textContent || b.value || ""); }).join(" ");
        const quiereGuardar = pn.length <= 3 && (
            /\b(guardar|guarda|guardalo|confirmar|confirma|registrarlo|finalizar|finaliza|terminar|termina)\b/.test(t) ||
            (/^(registrar|registra)\b/.test(t) && (pn.length === 1 || textoBoton.indexOf(pn[pn.length - 1]) !== -1))
        );
        if (quiereGuardar) {
            cancelarGuardadoProgramado();
            mostrarMensaje(texto, "usuario");
            mostrarMensaje("Guardando...", "bot");
            animar("Brincar");
            window.setTimeout(guardarAhora, 700);
            return true;
        }

        /* Cancelar: detiene la cuenta regresiva o, si no hay, sale del formulario */
        if (pn.length <= 3 && /^(cancelar|cancela|descartar|no guardes|detente)\b/.test(t)) {
            mostrarMensaje(texto, "usuario");
            if (cancelarGuardadoProgramado()) {
                mostrarMensaje("Listo, no lo guardé. Puedes seguir editando o decir «guardar».", "bot");
                return true;
            }
            mostrarMensaje("Cancelado. Volviendo a la página anterior.", "bot");
            try { sessionStorage.setItem("naranjitaAbierto", "1"); } catch (e) {}
            window.setTimeout(function () { window.history.back(); }, 700);
            return true;
        }

        /* Venta con varias líneas de productos */
        if (formularioConLineas() && ejecutarEnVentas(texto, t)) return true;

        /* "¿qué campos ves?" */
        if (/\bcampos\b/.test(t) && /\b(que|cuales|dime|lista|muestra|ves|hay|tiene)\b/.test(t)) {
            mostrarMensaje(texto, "usuario");
            mostrarMensaje("En este formulario veo: " + listaDeCampos(campos) + ".", "bot");
            return true;
        }

        /* "<campo> <valor>", por ejemplo "teléfono 300 123 4567" */
        const palabras = texto.trim().split(/\s+/);
        for (const grupo of ALIAS_CAMPOS) {
            for (const alias of grupo.alias) {
                const n = alias.split(" ").length;
                if (pn.slice(0, n).join(" ") !== alias) continue;

                let resto = palabras.slice(n);
                if (resto.length && /^(es|son|de|del)$/.test(normalizar(resto[0]))) resto = resto.slice(1);
                const valor = resto.join(" ").trim();
                if (!valor) return false;

                const campo = buscarCampo(campos, grupo.claves);
                mostrarMensaje(texto, "usuario");
                if (!campo) {
                    mostrarMensaje("No encontré un campo «" + alias + "» en este formulario. Veo estos: " + listaDeCampos(campos) + ".", "bot");
                    return true;
                }

                const nombrePropio = grupo.claves[0] === "nombre" || grupo.claves[0] === "apellido";
                let dato = nombrePropio ? titulo(valor) : valor;
                if (grupo.cifra) {
                    const n = aNumero(valor);
                    if (!isNaN(n)) dato = String(n);
                }
                if (grupo.fecha) {
                    dato = aFecha(valor);
                    if (!dato) {
                        mostrarMensaje("No entendí la fecha. Dime por ejemplo «fecha hoy», «fecha ayer» o «fecha 15 de noviembre».", "bot");
                        return true;
                    }
                }
                if (rellenar(campo, dato, grupo.numerico)) {
                    mostrarMensaje("Listo, puse " + (etiquetaDe(campo) || alias).toLowerCase() + ": " + valorVisible(campo) + ". " + resumenFormulario(), "bot");
                    programarGuardado();
                } else if (ambiguedad.length) {
                    mostrarMensaje("Hay varios que coinciden con «" + valor + "»: " + ambiguedad.join(", ") + ". Dime el nombre completo.", "bot");
                } else if (campo.tagName === "SELECT") {
                    const opciones = Array.from(campo.options).map(function (o) { return o.text.trim(); })
                        .filter(function (o) { return o && o.indexOf("---") === -1; }).slice(0, 8).join(", ");
                    mostrarMensaje("No encontré «" + valor + "» en la lista. Las opciones son: " + opciones + ".", "bot");
                } else {
                    mostrarMensaje("No pude poner «" + valor + "» en ese campo.", "bot");
                }
                return true;
            }
        }

        return false;
    }

    /* "registrar cliente Felipe Rojas" → "Felipe Rojas" */
    function extraerNombre(texto, entidad) {
        if (["cliente", "proveedor", "producto"].indexOf(entidad.clave) === -1) return "";
        const m = texto.match(/\b(?:clientes?|proveedor(?:es)?|productos?)\b[\s,:]*(?:llamad[oa]|de nombre|que se llama|con nombre|nombre)?[\s,:]*(.*)$/i);
        const valor = ((m && m[1]) || "").trim();
        if (!valor || /^(numero|número|id|n°|#)/i.test(valor) || /^\d+$/.test(valor)) return "";
        return titulo(valor);
    }

    function irA(ruta, mensaje) {
        mostrarMensaje(mensaje, "bot");
        animar("Brincar");
        try { sessionStorage.setItem("naranjitaAbierto", "1"); } catch (e) {}
        window.setTimeout(function () {
            window.location.href = ruta;
        }, 900);
    }

    /* Devuelve true si la frase era un comando y ya lo ejecutó */
    function ejecutarComando(texto) {
        const t = normalizar(texto);
        const palabras = t.split(/\s+/).filter(Boolean);

        if (!t || palabras.length > 10 || NO_ES_COMANDO.test(t)) return false;

        /* Tema */
        if (/\b(modo|tema)\b.*\boscuro\b|\boscuro\b/.test(t) || /\b(modo|tema)\b.*\bclaro\b|\bclaro\b/.test(t)) {
            const quiereOscuro = /oscuro/.test(t);
            const boton = document.getElementById("temaBtn");
            const actual = document.documentElement.getAttribute("data-theme");
            mostrarMensaje(texto, "usuario");
            if (boton && ((quiereOscuro && actual !== "dark") || (!quiereOscuro && actual === "dark"))) {
                boton.click();
            }
            mostrarMensaje(quiereOscuro ? "Listo, modo oscuro." : "Listo, modo claro.", "bot");
            animar("Brincar");
            return true;
        }

        /* Atrás */
        if (/\b(atras|volver|regresar)\b/.test(t)) {
            mostrarMensaje(texto, "usuario");
            mostrarMensaje("Volviendo a la página anterior.", "bot");
            try { sessionStorage.setItem("naranjitaAbierto", "1"); } catch (e) {}
            window.setTimeout(function () { window.history.back(); }, 700);
            return true;
        }

        /* Cerrar sesión */
        if (/cerrar sesion|salir del sistema/.test(t)) {
            const salir = document.querySelector(".logout-btn");
            if (salir) {
                mostrarMensaje(texto, "usuario");
                mostrarMensaje("Cerrando sesión. ¡Hasta pronto!", "bot");
                animar("Saludar");
                window.setTimeout(function () { salir.click(); }, 1200);
                return true;
            }
            return false;
        }

        const esperaba = esperandoRegistro && (Date.now() - esperandoRegistro) < 30000;
        const quiereCrear = VERBO_CREAR.test(t) || esperaba;

        /* Los usuarios no se registran por voz */
        if (quiereCrear && /\busuarios?\b/.test(t)) {
            esperandoRegistro = 0;
            mostrarMensaje(texto, "usuario");
            mostrarMensaje("Por seguridad, los usuarios no se pueden registrar por voz. Hazlo desde el sistema.", "bot");
            return true;
        }

        const entidad = ENTIDADES.find(function (e) { return e.patron.test(t); });
        if (!entidad) {
            /* Dijo solo "registrar": pregunta qué */
            if (VERBO_CREAR.test(t)) {
                esperandoRegistro = Date.now();
                mostrarMensaje(texto, "usuario");
                mostrarMensaje("¿Qué quieres registrar? Puedo con cliente, producto, proveedor, venta, pedido o reembolso. Dime por ejemplo «cliente Felipe Rojas».", "bot");
                rearmarModoFormulario();
                return true;
            }
            return false;
        }

        /* Registrar / crear algo nuevo */
        if (quiereCrear) {
            esperandoRegistro = 0;
            const ruta = RUTAS.registrar && RUTAS.registrar[entidad.clave];
            mostrarMensaje(texto, "usuario");
            if (ruta) {
                const nombreDicho = extraerNombre(texto, entidad);
                try { sessionStorage.setItem("naranjitaPendiente", JSON.stringify({ valor: nombreDicho })); } catch (e) {}
                irA(ruta, "Abriendo el formulario de " + entidad.nombre.toLowerCase() +
                    (nombreDicho ? " con el nombre " + nombreDicho + "." : "."));
            } else {
                mostrarMensaje("No encontré la pantalla para registrar en " + entidad.nombre + ". Puedes entrar por el menú.", "bot");
            }
            return true;
        }

        /* Ir a una sección */
        let ruta = RUTAS[entidad.clave];
        if (entidad.clave === "grupo" && !document.querySelector('.sidebar-nav a[href="' + ruta + '"]')) {
            ruta = "";   /* Grupos solo existe para el superusuario */
        }

        mostrarMensaje(texto, "usuario");
        if (ruta) {
            irA(ruta, "Llevándote a " + entidad.nombre + ".");
        } else {
            mostrarMensaje("No tienes acceso a " + entidad.nombre + " o no encontré esa pantalla.", "bot");
        }
        return true;
    }

    /* ---------- Escucha manos libres con la palabra clave "Naranjita" ---------- */
    const ACTIVAR_COMANDO = /\b(activa|activar|activame|enciende|prende|inicia|empieza|comienza)\b.*(comando|voz|escuch)|\b(escuchame|dime|me escuchas|estas ahi)\b/;
    const DESACTIVAR_VOZ = /\b(desactiva|desactivar|apaga|apagar|deten|detener|deja de|para de|silencio)\b.*(comando|voz|escuch)/;

    let reconocimiento = null;
    let escuchaActiva = false;      /* interruptor del micrófono */
    let modoComando = false;        /* true = la siguiente frase es una orden */
    let inicioManual = false;       /* true si la persona pulsó el micrófono */
    let temporizadorComando = null;
    let reinicio = null;
    let erroresSeguidos = 0;
    const placeholderOriginal = entrada.placeholder;
    const esBrave = !!(navigator.brave && navigator.brave.isBrave);
    let audioCtx = null;

    /* Pitido corto para avisar que Naranjita te escuchó */
    function pitido(agudo) {
        try {
            audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
            const osc = audioCtx.createOscillator();
            const vol = audioCtx.createGain();
            osc.frequency.value = agudo ? 880 : 440;
            vol.gain.value = 0.05;
            osc.connect(vol);
            vol.connect(audioCtx.destination);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.12);
        } catch (e) {}
    }

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

    function entrarModoComando() {
        modoComando = true;
        pintarEstado();
        pitido(true);
        abrirChat();
        mostrarMensaje("Te escucho. Dime qué necesitas.", "bot");
        window.clearTimeout(temporizadorComando);
        temporizadorComando = window.setTimeout(salirModoComando, 9000);
    }

    function ejecutarOrden(texto) {
        const t = normalizar(texto);
        const limpio = texto.charAt(0).toUpperCase() + texto.slice(1);

        if (DESACTIVAR_VOZ.test(t)) {
            apagarEscucha(true);
            return;
        }

        abrirChat();
        entrada.value = "";
        if (ejecutarEnFormulario(limpio)) {
            rearmarModoFormulario();
            return;
        }
        if (!ejecutarComando(limpio)) {
            enviarMensaje(limpio);
        }
    }

    /* Se llama con cada frase que el navegador termina de reconocer */
    function alEscuchar(texto) {
        const t = normalizar(texto);
        if (!t) return;

        const sinClave = texto.replace(/^.*?\bnaranjit[ao]s?\b[\s,.:;!?¡¿-]*/i, "").trim();

        /* Ya dijo "Naranjita": esta frase es la orden */
        if (modoComando) {
            salirModoComando();
            ejecutarOrden(/\bnaranjit[ao]s?\b/.test(t) ? sinClave : texto);
            return;
        }

        /* Esperando la palabra clave */
        if (!/\bnaranjit[ao]s?\b/.test(t)) return;

        const resto = normalizar(sinClave);
        if (DESACTIVAR_VOZ.test(resto)) {
            apagarEscucha(true);
            return;
        }
        if (!resto || ACTIVAR_COMANDO.test(resto)) {
            entrarModoComando();
            return;
        }
        pitido(true);
        ejecutarOrden(sinClave);
    }

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
            if (modoComando) {
                entrada.value = provisional;
            }
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

        /* Chrome corta la escucha cada cierto tiempo: se vuelve a encender sola */
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
            mostrarMensaje("Escucha activada. Di «Naranjita» y después tu orden, por ejemplo: «Naranjita, productos» o «Naranjita, registrar cliente». También puedes decir solo «Naranjita, activa el comando de voz».", "bot");
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

    if (microfono) {
        if (!Reconocimiento) {
            microfono.style.display = "none";   /* Firefox y otros no la soportan */
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

    /* Si venimos de "registrar cliente Felipe Rojas", llena el nombre al llegar */
    (function aplicarPendiente() {
        let pendiente = null;
        try {
            const guardado = sessionStorage.getItem("naranjitaPendiente");
            if (guardado) {
                pendiente = JSON.parse(guardado);
                sessionStorage.removeItem("naranjitaPendiente");
            }
        } catch (e) {}
        if (!pendiente) return;

        window.setTimeout(function () {
            const campos = camposDelFormulario();
            if (campos.length < 2) return;

            /* Dijo "registrar cliente" sin nombre: queda lista para recibir los datos */
            if (!pendiente.valor && formularioConLineas()) {
                mostrarMensaje("Formulario de venta abierto. Dime el cliente, por ejemplo «cliente Felipe Rojas»; luego los productos, por ejemplo «producto agua micelar cantidad 2»; después el «abono 50000», y al final «registrar venta».", "bot");
                rearmarModoFormulario();
                return;
            }
            if (!pendiente.valor) {
                mostrarMensaje("Formulario abierto. Dime los datos, por ejemplo «nombre Felipe Rojas» o «teléfono 300 123 4567». Cuando no falte nada, lo registro.", "bot");
                rearmarModoFormulario();
                return;
            }

            const campoNombre = buscarCampo(campos, ["nombre"]);
            const campoApellido = buscarCampo(campos, ["apellido"]);
            if (!campoNombre) {
                mostrarMensaje("Abrí el formulario, pero no encontré el campo del nombre. Escríbelo tú.", "bot");
                return;
            }

            const partes = pendiente.valor.split(/\s+/);
            if (campoApellido && campoApellido !== campoNombre && partes.length > 1) {
                rellenar(campoNombre, partes[0], false);
                rellenar(campoApellido, partes.slice(1).join(" "), false);
            } else {
                rellenar(campoNombre, pendiente.valor, false);
            }

            mostrarMensaje("Abrí el formulario y escribí «" + pendiente.valor + "». " + resumenFormulario(), "bot");
            animar("Brincar");
            rearmarModoFormulario();
            programarGuardado();
        }, 700);
    })();

    /* Después de guardar, cuenta cómo salió */
    (function resultadoDeGuardado() {
        let hubo = false;
        try {
            hubo = sessionStorage.getItem("naranjitaGuardando") === "1";
            sessionStorage.removeItem("naranjitaGuardando");
        } catch (e) {}
        if (!hubo) return;

        window.setTimeout(function () {
            if (document.querySelector(".mensaje-sistema.success")) {
                mostrarMensaje("¡Listo! Quedó registrado.", "bot");
                animar("Brincar", 2);
            } else if (camposDelFormulario().length >= 2) {
                mostrarMensaje("No se pudo guardar. Revisa los campos marcados en la página y dime lo que falta.", "bot");
                rearmarModoFormulario();
            } else {
                mostrarMensaje("Listo, envié el formulario.", "bot");
            }
        }, 700);
    })();

    formulario.addEventListener("submit", function (evento) {
        evento.preventDefault();
        enviarMensaje(entrada.value);
    });

    document.querySelectorAll(".asistente-sugerencia").forEach(function (boton) {
        boton.addEventListener("click", function () {
            enviarMensaje(boton.textContent);
        });
    });

    /* Si venimos de un comando de voz, el chat se queda abierto en la página nueva */
    try {
        if (sessionStorage.getItem("naranjitaAbierto") === "1") {
            sessionStorage.removeItem("naranjitaAbierto");
            ventana.classList.add("abierto");
            if (invitacion) {
                invitacion.style.display = "none";
            }
        }
    } catch (e) {}

    mostrarMensaje(
        "¡Hola! Soy Naranjita, el asistente virtual de MisMary. Puedes preguntarme sobre productos, inventario, ventas, pedidos y otras funciones de la tienda.",
        "bot"
    );

});