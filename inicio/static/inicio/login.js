// Mostrar u ocultar la contraseña en el formulario de inicio de sesión.
document.querySelectorAll('.toggle-password').forEach(function (button) {
  const input = document.getElementById(button.dataset.target);
  if (!input) {
    return;
  }

  button.addEventListener('click', function () {
    const start = input.selectionStart;
    const end = input.selectionEnd;
    const mostrar = input.type === 'password';

    input.type = mostrar ? 'text' : 'password';

    const etiqueta = mostrar ? 'Ocultar contraseña' : 'Mostrar contraseña';
    button.setAttribute('aria-pressed', String(mostrar));
    button.setAttribute('aria-label', etiqueta);
    button.setAttribute('title', etiqueta);

    const icono = button.querySelector('i');
    if (icono) {
      icono.classList.toggle('bi-eye', mostrar);
      icono.classList.toggle('bi-eye-slash', !mostrar);
    }

    // Devuelve el foco al campo sin perder la posición del cursor.
    input.focus({ preventScroll: true });
    try {
      input.setSelectionRange(start, end);
    } catch (error) {
      // Algunos navegadores no permiten manejar la selección; el foco basta.
    }
  });
});

// Copiar el usuario demo de cada fila del mini prompt de roles y rellenar el campo.
function copiarConAreaDeTexto(texto) {
  const area = document.createElement('textarea');
  area.value = texto;
  area.setAttribute('readonly', '');
  area.style.position = 'fixed';
  area.style.top = '-1000px';
  area.style.opacity = '0';
  document.body.appendChild(area);
  area.select();
  const copiado = document.execCommand('copy');
  document.body.removeChild(area);
  if (!copiado) {
    throw new Error('No se pudo copiar');
  }
}

// Un click copia el usuario, lo escribe en el campo Usuario y deja el cursor
// en Contraseña, para no tener que teclear ni pegar nada.
function rellenarUsuario(texto) {
  const campo = document.querySelector('input[name="username"]');
  if (!campo) {
    return false;
  }
  campo.value = texto;
  if (typeof Event === 'function') {
    campo.dispatchEvent(new Event('input', { bubbles: true }));
    campo.dispatchEvent(new Event('change', { bubbles: true }));
  }
  return true;
}

function enfocarContrasena() {
  const campo = document.querySelector('input[name="password"]');
  if (campo) {
    campo.focus({ preventScroll: true });
  }
}

document.querySelectorAll('.copy-user').forEach(function (button) {
  const texto = button.dataset.copy;
  if (!texto) {
    return;
  }
  const icono = button.querySelector('i');
  const etiquetaOriginal = button.getAttribute('aria-label');
  const tituloOriginal = button.getAttribute('title');
  let temporizador = null;

  function restaurar() {
    if (icono) {
      icono.classList.add('bi-clipboard');
      icono.classList.remove('bi-check2');
    }
    button.setAttribute('aria-label', etiquetaOriginal);
    button.setAttribute('title', tituloOriginal);
    temporizador = null;
  }

  function avisar(textoAviso, iconoAviso) {
    if (temporizador) {
      clearTimeout(temporizador);
    }
    if (icono) {
      icono.classList.remove('bi-clipboard');
      icono.classList.add(iconoAviso);
    }
    button.setAttribute('aria-label', textoAviso);
    button.setAttribute('title', textoAviso);
    temporizador = setTimeout(restaurar, 1500);
  }

  button.addEventListener('click', async function () {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(texto);
      } else {
        copiarConAreaDeTexto(texto);
      }
      const rellenado = rellenarUsuario(texto);
      if (rellenado) {
        enfocarContrasena();
        avisar('Usuario ' + texto + ' escrito en el campo', 'bi-check2');
      } else {
        avisar('Usuario copiado: ' + texto, 'bi-check2');
      }
    } catch (error) {
      avisar('No se pudo copiar el usuario', 'bi-x-lg');
    }
  });
});
