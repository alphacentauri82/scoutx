# ScoutX

ScoutX es una aplicación creada en python con flask el cual incluye jinja2 como template engine, lo que nos permite separar la logica de la aplicacion de la presentacion de los datos. Del lado del cliente se usará javascript para desarrollar ciertas funcionalidades dinámicas requeridas en nuestra App.

# Características de la aplicación

ScoutX permite hacer ping al nightscout de un usuario particular obteniendo el ultimo nivel de glucosa registrado. Si los niveles estan abajo de 70 o arriba de 240, la aplicacion ejecutara una llamada al celular personal del usuario reproduciendo un speech indicandole su nivel de glucosa. 
Si el usuario no responde se enviara un sms al numero favorito seleccionado por el usuario y 5 numeros adicionales tambien seleccionados por el usuario. 

La frecuencia del ping realizado a nightscout sera de 1 minuto. Para ser exactos se hara en el segundo 30 de cada minuto usando el reloj del sistema. Lo que indica que si el nivel de glucosa de un usuario siguen fuera del rango aceptado durante ese periodo de tiempo se volvera a realizar la llamada. Lo ideal es indicar al sistema que si se ha llamado recientemente al usuario que el app espere 120 segundos para volver a ejecutar el workflow de la llamada.

Si el servicio de nightscout para un usuario en particular no responde por 1 hora, se enviara un sms indicando al usuario que su servicio de nightscout esta caido.

El usuario podra logearse usando google y configurar la siguiente informacion: Nightscout Api Url, numero personal, numero favorito y podra agregar 5 numeros de telefono adicionales, el usuario tendra la opcion de no agregar ningun numero adicional.

# Aplicaciones involucradas

nexmo-nsnotifier se apoya en 4 aplicaciones para su funcionamiento.

- Nightscout: Es una aplicacion que indica en tiempo real el nivel de glucosa en la sangre de un usuario. Para ello se debe contar con un dispositivo que calcula el nivel de glucosa en la sangre (CGM) el cual esta conectado al usuario, el dispositivo obtiene los datos y nightscout los ingresa a una base de datos de MongoDB. 

  A su vez nightscout cuenta con un API que permite obtener los datos con formato json o xml para su uso en aplicaciones externas. Probablemente sea necesario habilitar CORS en el nightscout del usuario para poder tener acceso a esta informacion desde dominios externos.

  Puede obtener mas informacion en el siguiente link https://github.com/nightscout/cgm-remote-monitor


- Nexmo: Es una plataforma que pone a disposicion un conjunto de APIs atraves de los cuales fascilita la comunicacion entre empresas y clientes. Estos servicios de comunicacion estan entre llamadas de voz, conferencias, mensajes de texto e incluso mensajes usando los canales de Facebook messenger, whatsapp y viber.

  Para lograr esto el usuario necesita tener una cuenta en nexmo, crear una aplicacion en nexmo (en donde indica el o los servicios que ofrecera el App), crear un numero virtual de nexmo y contar con el saldo suficiente para ofrecer los servicios que requiera.

  Acceder al siguiente enlace para consultar mas informacion https://developer.nexmo.com/

- Google Auth: El Api que nos permite usar el servicio de autenticacion de google desde nuestra aplicacion web. Mas informacion en https://developers.google.com/identity/protocols/OAuth2

- Firebase / Firestore. Firebase proporciona multiples servicios por ejemplo base de datos en tiempo real, almacenamiento, web services (usando functions) y mucho mas. En nuestro caso usaremos el servicio firestore de firebase para almacenar nuestros datos en la nube.

# Analisis

Dado lo expuesto en la seccion de caracteristicas podemos concluir que nuestra aplicacion puede dividirse en dos partes:

- Una aplicacion en Flask que permita al usuario logearse y configurar los datos de la aplicacion
- Un Thread de python con un scheduler que se ejecute con una frecuencia dada, consultando el nightscout de cada usuario de la aplicacion. y enviando las alertas en los casos que sea necesario. Puede asignarse un segundo scheduler que se ejecute con menos frecuencia, para obtener datos frescos.

# Requerimientos

Antes de comenzar con el desarrollo de las funcionalidades descritas en la seccion anterior, revisaremos ciertas caracteristicas necesarias instalar modulos de python o garantizar la ejecucion de nuestra aplicacion.

- La terminal de linux (Os x esta basado en Unix asi que tambien cuenta). Esta aplicacion fue desarrollada con ubuntu, debian y ha sido probada tambien en WSL.

- Nuestra aplicacion usara python 3, para confirmar nuestra version de python, abrimos nuestra terminal y ejecutamos el siguiente comando:

  ```
  python --version
  ```

  Si el resultado es `python 3.x.x` podemos continuar con el siguiente paso. Caso contrario debemos proceder a instalar python 3. 

- Comprobar la version de pip (Python module installer). pip se incluye por defecto en caso que tengamos python 3 instalado.

  ```
  pip --version
  ```

  **Nota:** El comando anterior deberia devolver la version de pip actual e indicarnos con que version de python trabaja pip. Es importante garantizar python 3 aparezca como la version usada por pip

- Una vez que hemos verificado que tenemos python 3, procedemos a crear el directorio de nuestra apllicacion e ingresamos al mismo

  ```
  mkdir nexmo-nsnotifier
  cd nexmo-nsnotifier
  ```

- Dado que la parte visual es la que estaremos desarrollando (Login y configuracion de los datos). Procedemos a instalar flask

  ```
  pip install Flask
  ```

  **Nota:** pip instalara las dependencias necesarias para Flask de manera automatica. Por ejemplo Jinja (El template engine de flask).

# 1. Desarrollo de Interface de usuario para login con google auth

En este aparatado iniciaremos configurando Google Auth. Y con Flask procederemos a crear una interface sencilla que nos permita usar el Google Auth API, logearnos y crear una session persistente del lado del server para mantenernos logeados hasta que el usuario decida salir de sesion.

### Google Auth

Para ello necesitamos obtener un client ID, el cual usaremos para llamar el sign in API de Google. Abrimos el navegador y escribimos: https://console.cloud.google.com/home/dashboard , Si ya existe un proyecto creado se cargara automaticamente. En caso contrario tendremos que crear un nuevo proyecto.

Una vez creado el proyecto hacemos click en el `menu de navegacion (≡)` y seleccionamos la opcion `Apis y servicios > credenciales` una vez dentro hacemos clic en el boton `Crear credenciales > ID de cliente de OAuth`, se nos presentara un form consultandonos que tipo de aplicacion estamos desarrollando, en nuestro caso seleccionamos la opcion `Web` y en los campos `Orígenes de JavaScript autorizados` y `URIs de redirección autorizados` escribimos el nombre del dominio que usaremos para nuestra aplicacion `E.g. https://domain.ext/`, en nuestro caso asumiremos que `/` sera el endpoint que consumira nuestro servicio de autenticacion.

Hacemos clic en el boton crear y nuestro client ID sera generado. El mismo deberia aparecer listado en la seccion llamada `IDs de cliente de OAuth 2.0`. mantener el client ID a mano, ya que lo usaremos posteriormente en nuestra aplicacion.

### Preparativos

Procedemos a hacer una recapitulacion de las cosas que necesitamos alcanzar el objetivo expuesto anteriormente, entre estas se requiere: 

- Usar el **clientID**: el cual lo obtendremos desde un archivo `.env` (donde almacenaremos varias variables de entorno). Para obtener esos valores usaremos el modulo dotenv y su funcion load_dotenv. 

- Los modulos de google: Para re-confirmar la identidad del usuario conectado del lado de backend.

- Los modulos de Flask, que nos permitiran manejar los request, cargar los templates y crear las variables de session

**`dotenv`, `requests` y los `modulos de google` no son nativos de python**, por esa razon abrimos la terminal y procedemos a instalarlo:

  ```
  pip install requests python-dotenv google-auth
  ```

- Otro detalle adicional: Flask necesita un key unico para almacenar nuestras variables de session. El mismo es un binario que tenemos que manejar discretamente. Siempre en la terminal ejecutamos el siguiente comando para generarlo:

  ```
  python -c 'import os; print(os.urandom(16))'
  ```

### El codigo fuente

Una vez hecho eso abrimos nuestro editor preferido (por ejemplo pyCharm o visual studio code). Dentro de nuestro editor abrimos el directorio del proyecto y agregamos un nuevo archivo y le asignamos el nombre que deseemos, en mi caso `superdi.py`.

Agregamos las siguientes lineas de codigo:

Archivo `superdi.py`

En la parte superior del archivo importaremos los siguientes modulos


Esta linea indica que del modulo flask estaremos importando las clases y funciones mencionadas
E.g. render_template es una funcion que nos cargara el template que indiquemos en nuestro codigo
Mientras que Flask, es la clase que nos permitira inicializar nuestra aplicacion

```python
import json, os
from flask import Flask, request, render_template, session
```

De igual manera importamos algunas funciones que nos permitiran leer las variables de entorno. Una forma segura de manejar credenciales es que se encuentren
disponibles solamente en el ambito del sistema operativo que ejecuta la aplicacion.

```python
from os.path import join, dirname
from dotenv import load_dotenv
```

Incluimos los modulos de python para google auth que nos permitiran reconfirmar la identidad del usuario desde el backend
Esto nos permitira crear una sesion persistente si la identidad es valida

```python
from google.oauth2 import id_token
import google.auth.transport.requests
```

Y Modulo que nos permite hacer request usando los metodos POST o GET. Es similar a Axios

```python
import requests
```

Desde nuestro editor creamos un nuevo archivo y lo nombramos `.env`. Agregamos la siguiente linea al archivo:

```ruby
GOOGLE_CLIENT_ID="YOUR_GOOGLE_AUTH_CLIENT_ID"
SITE_URL="YOUR_SITE_URL"
```

**Nota:** Reemplazamos el texto `YOUR_GOOGLE_AUTH_CLIENT_ID` con el clientID generado por google y `YOUR_SITE_URL` con la url que usaremos para desplegar nuestra app ejemplo `https://domain.ext`. y guardamos el archivo

Regresamos al archivo superdi.py y agregamos al final del archivo las siguientes lineas

```python
app = Flask(__name__)
app.secret_key = b'U\xd5Q\xbfX\xaf\xd0\xfd\x8a\xb7=\xc2\xc0y*%'
```
Asignamos la variable `app` que representa nuestro Flask Application, app creara su propio contexto para hacer solamente operaciones relacionadas con los request se realicen a la aplicacion de flask

A continuacion le asignamos el atributo secret_key. **Fijarse en la letra `b''`, esto indica que el valor que esta esperando el atributo es binario**. Aca se asigna el valor previamente generado por el comando python -c 'import os; print(os.urandom(16))'

Para tener acceso a las variables de entorno definidas en el archivo `.env`, agregamos las lineas:
```python
envpath = join(dirname(__file__),"./.env")
load_dotenv(envpath)
```

Definimos la funcion get_session que evalua si existe un key especifico dentro de la variable de sesion. Retornando `None` en caso que no exista
en caso contrario se retorna el valor del key. La misma puede ser reutilizada en diferentes secciones del programa

```python
def get_session(key):
    value = None
    if key in session:
        value = session[key]
    return value
```

En esta seccion comenzamos a definir nuestra aplicacion de Flask. A continuacion se crea el controller para el endpoint `/` que sera nuestro landing page y que nos mostrara el boton de login de google.

```python
@app.route('/',methods=['GET','POST'])
def home():
    if get_session("user") != None:
        return render_template("home.html", user = get_session("user"))
    else:
        return render_template("login.html", client_id=os.getenv("GOOGLE_CLIENT_ID"), site_url=os.getenv("SITE_URL"))
```

La linea `@app.route('/',methods=['GET','POST'])` indica que todo request sea GET o POST sera redirigido al handler `home()` en donde se evalua si la sesion del usuario existe (es decir el usuario esta autenticado) se cargue el template `home.html` (cuando este template es cargado se le pasa la variable user para tener acceso a los datos del usuario autenticado desde el template), en caso contrario cargamos el template `login.html` en donde se mostrara la interface de autenticacion de google (Pasamos el valor de la variable de entorno `GOOGLE_CLIENT_ID` y el `SITE_URL` definida previamente en nuestro `.env`, este segundo parametro lo usaremos para redireccionamiento)

Siguiendo el Workflow cuando el usuario ingrese al sitio la variable de sesion user no existira, por ende login.html sera cargado. El siguiente paso logico seria desarrollar el `home.html` jinja template. Pero previo a eso necesitamos configurar los siguientes detalles:

- Descargar los archivos de `materialize` un framework para el desarrollo del front-end de nuestras aplicaciones basado en material design:
  Para acceder a archivos estaticos (css, js, images, fonts) Flask por defecto reconoce el directorio `static` con esta finalidad. Desde nuestro editor procedemos a crear el directorio static o bien desde la terminal ejecutando el comando `mkdir static`

  Abrimos nuestro navegador y cargamos la siguiente url: https://materializecss.com/getting-started.html. Hacemos click sobre el boton de descarga de Materialize. Descomprimimos el archivo, movemos los directorios `css` y `js` dentro del directorio `static` creado previamente. Lo ideal es quedarnos solamente con las versiones minificadas de los archivos css y js.

  En el caso de los iconos de materialize pueden ser descargados desde https://fonts.googleapis.com/icon?family=Material+Icons, una vez descargado el archivo del font podemos crear el subdirectorio `static/fonts` ubicar el archivo del font dentro.

  Dentro del directorio `static/css/` agregamos un nuevo archivo llamado `style.css` en donde ubicaremos los estilos de nuestra aplicacion. Ciertamente materialize es mas que suficiente para proporcionar los estilos de nuestra App pero a veces es necesario un archivo de estilo propio para controlar ciertos detalles no contemplados en materialize.

  ```css
    @font-face {
    font-family: 'Material Icons';
    font-style: normal;
    font-weight: 400;
    src: url(/static/fonts/google-icons.woff2) format('woff2');
    }

    .material-icons {
    font-family: 'Material Icons';
    font-weight: normal;
    font-style: normal;
    font-size: 24px;
    line-height: 1;
    letter-spacing: normal;
    text-transform: none;
    display: inline-block;
    white-space: nowrap;
    word-wrap: normal;
    direction: ltr;
    -moz-font-feature-settings: 'liga';
    -moz-osx-font-smoothing: grayscale;
    }

    .logo{
    font-size:30px !important;
    padding-top:5px;
    }

    div.g-signin2{
    margin-top:10px;
    }

    div.g-signin2 div{
    margin:auto;
    }
    div#user{
    margin-top:10px;
    margin-bottom:10px;
    }
    div#user.guest{
    text-align:center;
    font-size:20px;
    font-weight:bold;
    }
    div#user.logged{
    text-align:right;
    }
    div#user.logged a{
    margin-left:10px;
    }
    body{
    display: flex;
    min-height: 100vh;
    flex-direction: column;
    }
    main {
    flex: 1 0 auto;
    }
    div.add_contact{
    height:20px;
    }
    div.add-contacts-container{
    padding-bottom:40px !important;
    }
    .input-field .sufix{
    right:0;
    }
    i.delete{
    cursor:pointer;
    }
  ```

- El segundo detalle a desarrollar es el layout de nuestra aplicacion. Un template padre que define bloques de contenidos que son usados por otros archivos hijos. Oficialmente este seria nuestro primer template en jinja. Para que este archivo sea reconocido por Flask como un template procedemos a usar el editor y creamos el directorio `templates`, este debe quedar al mismo nivel que el directorio `static`. Dentro de este directorio creamos un nuevo archivo llamado `layout.html` al cual agregamos el siguiente codigo:

```html
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/materialize.min.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    {% block head %}{% endblock %}
    </head>
    <body>
    <header class="container-fluid">
    <nav class="teal">
        <div class="container">
        <div class="row">
        <div class="col">
        <a href="#" class="brand-logo"><i class="material-icons logo">record_voice_over</i> ScoutX</a>
        </div>
        </div>
        </div>
    </nav>
    </header>
    <main class="container">
        {% block content %}{% endblock %}
    </main>
    <footer class="page-footer teal">
    <div class="footer-copyright"> 
        <div class="container">
        ScoutX 2021
        </div>
    </div>
    </footer>
    <script language="javascript" src="{{ url_for('static', filename='js/materialize.min.js') }}"></script>
    {% block script %}{% endblock %}
    </body>
    </html>
```

Dos detalles interesantes de este archivo son **El uso de bloques** y **el uso de la funcion `url_for`**. En el caso de los bloques son secciones reservadas para la insercion de codigo con jinja desde templates hijos. Si prestamos atencion la funcion `url_for` nos genera la url hacia los recursos de javascript y css apartir de `static` lo cual resulta bastante comodo y elegante.

La estructura de archivo que deberiamos tener hasta este punto deberia ser la siguiente:

```
    - static/
      - css/
        - materialize.min.css
      - fonts/
        - google-icons.woff2
      - js/
        - materialize.min.js
    - templates/
    - layout.html
    .env
    - superdi.py
```

Con los detalles anteriores garantizados, creamos el archivo `login.html` dentro del directorio `templates`. Este archivo sera cargado cuando la variable de sesion `user` no exista (es decir el usuario no esta logeado)

  ```html
    {% extends "layout.html" %}
    {% block head %}
    <script src="https://apis.google.com/js/platform.js" async defer></script>
    <meta name="google-signin-client_id" content="{{ client_id }}">
    {% endblock %}
    {% block content %}
    <div id="user" class="guest">Welcome guest, You need to authenticate</div>
    <div class="row">
        <div class="col s6 offset-s3">
        <div class="card blue-grey darken-1">
            <div class="card-content white-text">
            <span class="card-title">Login To Enter Scout</span>
        <p>This application is going to allow you configure some alerts to your Phone, a Favorite Phone or 5 contact Phones. If you use a nightscout device and you have your api available for external queries. You can use this server and when the glucose level is to low and to high you will receive a call to indicates the glucose level. If you not Answer the call then an sms is sent to your favorite number and other 5 contact numbers.</p>
        <div class="g-signin2" data-onsuccess="onSignIn"></div>
            </div>
        </div>
        </div>
    </div>
    <script language="javascript">
    function onSignIn(googleUser) {
        var profile = googleUser.getBasicProfile();
        if(profile.getId()!==null && profile.getId()!==undefined){
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '{{ site_url|safe }}/login');
        xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
        xhr.onload = function() {
        console.log('Signed in as: ' + xhr.responseText);
        //Authenticated so redirect to index
        window.location = "{{ site_url|safe }}/";
        };
        xhr.send('idtoken=' + googleUser.getAuthResponse().id_token + "&username=" + profile.getName() + "&email=" + profile.getEmail());
        }
    }
    </script>
    {% endblock %}
  ```

En el script `login.html` template de jinja, podemos observar que la primera linea es `{% extends "layout.html" %}`. Este linea indica que `login.html` hereda de `layout.html` en otras palabras es un template hijo de layout. Esto significa que el renderer al final cargara `layout.html` con las variantes de codigo que nosotros agreguemos en `login.html`. Estas variantes estan definidas dentro de los bloques permitidos en layout. Dentro de `login.html` hacemos uso de los bloques `head` y `content`.

Dentro del bloque `head` se muestran las lineas:

```html
<script src="https://apis.google.com/js/platform.js" async defer></script>
<meta name="google-signin-client_id" content="{{ client_id }}">
```

La primera linea indica que estaremos usando el api de google en este caso para el proceso de autenticacion y la segunda es un meta usado por google para saber el clientID de nuestra aplicacion. Notar que dentro del atributo `content` hemos escrito `{{ client_id }}` cuando el compilador de jinja evalue esta expresion, nos imprimira el valor de la variable `client_id` que pasamos al template usando la funcion `render_template`.

El siguiente bloque definido es `content` y dentro del mismo presentamos un mensaje al usuario indicando como funciona la aplicacion. y despues se nos presentan unas lineas de codigo en javascript. Basicamente es una funcion conectada al evento `onSignIn`, esta es usada por google para devolver los datos del usuario que se logea usando autenticacion de google.

Obtenemos el perfil del usuario `googleUser.getBasicProfile()` y evaluamos que si existe Id el proceso de autenticacion fue exitoso y podemos proceder a enviarle algunos datos a nuestro server para que haga una reconfirmacion de identidad con google y a su vez cree la session.

```javascript
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '{{ site_url|safe }}/login');
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.onload = function() {
        console.log('Signed in as: ' + xhr.responseText);
        //Authenticated so redirect to index
        window.location = "{{ site_url|safe }}/";
    };
    xhr.send('idtoken=' + googleUser.getAuthResponse().id_token + "&username=" + profile.getName() + "&email=" + profile.getEmail());
```

Las lineas anteriores nos conectan a nuestro server usando una peticion (request) ajax. Poner atencion a la linea `xhr.open('POST', '{{ site_url|safe }}/login');` la misma indica el method que estara usando el request y la url. `{{ site_url|safe }}` sera reemplazado por el valor de la variable site_url que le pasamos al template. Para poder hacer la reconfirmacion nuestro flask application necesita solamente del `id_token`, sin embargo tambien pasamos el username y el email ya que los usaremos mas adelante para otras operaciones.

Una vez hecha la reconfirmacion nuestro server nos redirecionara a `/`. Si la reconfirmacion no fue exitosa el usuario tendra que intentar logearse una vez mas. Ahora bien, si observamos con cuidado aun no hemos definido el endpoint `/login` que sera encargado de hacer la reconfirmacion. Procedemos a crearlo, para ello regresar al archivo `superdi.py` en nuestro editor y agregar la siguientes lineas al final:

```python
@app.route('/login',methods=["POST"])
def login():
    try:
        token = request.form.get("idtoken")
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        infoid = id_token.verify_oauth2_token(token, google.auth.transport.requests.Request(), client_id)
        if infoid['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
        userid = infoid['sub']
        #Here is a good place to create the session
        session["user"] = {"userid": userid, "username": request.form.get("username"), "email": request.form.get("email")}
        return userid
    except ValueError:
        return "Error"
        pass

```

Como se ha mencionado anteriormente para hacer la reconfirmacion de la identidad del usuario en el server, solo necesitamos del id_token obtenido de la autenticacion de google y pasado a `/login` usando un ajax post request y del `client_id`, este lo obtenemos usando `os.getenv("GOOGLE_CLIENT_ID")`

Para hacer la reconfirmacion es recomendable ubicar nuestro codigo dentro de un `try` `except` block. Para manejo de excepciones en caso que se genere un error al momento de realizar la peticion. 

Esta verificacion se hace usando el metodo `verify_oauth2_token` y devuelve un `infoid` que debe tener un key `iss` que es una referencia al `issuer`, si el valor del issuer no coincide el domain de google asumiremos que la verficacion retorno un error y se generara una excepcion. Si por el contrario el response es valido procedemos a crear la sesion persistente del lado del server, asignando `user` al session object. Dentro de esta sesion almacenamos el userid, username y el email del usuario.

Hecho esto nuestro servidor retorna el response y el evento `xhr.onload` de nuestra peticion ajax es desencadenado. Cuya funcion es redirigirnos al `/` de nuestra aplicacion. En `/` nuestra aplicacion evalua si la sesion `user` existe y de ser asi cargara el template `home.html` pasandole el `session['user']` (Revisar superdi.py para confirmar la informacion)

Siguiendo la logica de nuestra aplicacion el siguiente paso es crear `home.html` dentro del directorio `templates`. Agregamos el siguiente codigo al archivo y guardamos el contenido:

```html
    {% extends "layout.html" %}
    {% block content %}
    <div id="user" class="logged">you are logged in as <b>{{ user.username }}</b> - <a id="logout" class="teal-text" href="/logout">Logout</a></div>
    {% endblock %}
```

Basicamente este template hereda de layout y en nuestro block `content` mostraremos el usuario logeado con google auth y el enlace `logout` para cerrar session. Este ultimo no esta programado, para completar la experiencia de logeo pasaremos a definir el endpoint `logout` dentro de `superdi.py`. Al final del archivo agregaremos las lineas:

```python
    @app.route('/logout')
    def logout():
        session.pop("user",None)
        return redirect(url_for('home'))
```

Nuestro `logout` endpoint elimina la sesion user y nos redirecciona a home. Home nuevamente evalua la sesion y al no encontrarla hara un render de `login.html`
**Nota:** url_for esta usando el nombre del handler `def home()` para la redireccion, no del endpoint. Aunque tambien es valido usar endpoints para redirecciones. En caso que `url_for` necesite generar una url en `https` la linea deberia ser de la siguiente forma: `url_for('home', _external=True, _scheme='https')` el parametro external indica generacion de una url absoluta y scheme el protocolo que deseamos se utilice. 

En  este punto nuestra aplicacion deberia ser capaz de logearse con google. Para desplegar nuestra applicacion es posible usar varios metodos, por ejemplo en nuestra terminal de linux podriamos escribir 

```sh
    export FLASK_APP=superdi
    flask run
```

Esto indica que ejecutaremos el app superdi.py. Sin embargo, lo recomendable es usar un server mas robusto que despliegue nuestra aplicacion y que permita un manejo mas eficiente de nuestras peticiones mejorando asi el rendimiento de la misma. Por ello usaremos gunicorn un servidor WSGI HTTP escrito en python compatible con multiples frameworks (Flask incluido).

Para instalarlo ejecutamos el siguiente comando en la terminal de linux:

```sh
    pip install gunicorn
```

Una vez instalado, desde la terminal de linux y estando dentro del directorio de nuestra aplicacion. Ejecutamos:

```sh
    gunicorn -b 0.0.0.0:80 superdi:app
```

Este comando hace deploy de nuestra aplicacion en nuestro server y escucha por peticiones usando el puerto 80. Con esto deberiamos ser capaces de entrar a nuestra aplicacion, logearnos con google y cerrar sesion.

**Nota:** Para detener nuestra aplicacion hacemos ctrl+c en la terminal de linux donde esta corriendo gunicorn

# 2. Almacenamiento de las configuraciones de nightscout por usuario con Firebase/Firestore

En esta seccion trabajaremos una interface simple en donde nuestro usuario podra agregar los siguientes datos: 

- **nightscout_api**: Una url valida de nightscout para obtener el nivel de glucosa del perfil asignado (estas urls tienen la nomenclarura https://`domain.ext`/api/v1/entries.json).
- **phone**: El numero de telefono personal del usuario donde desea recibir las alertas.
- **favorite_phone**: Numero de telefono favorito de un pariente o amigo cercano que pueda recibir las alertas 
- **phones**: Un arreglo con 5 numeros de telefono adicionales a quienes puedan llegar las alertas

Adicionalmente a ello nos interesa agregar tambien dos datos adicionales:

- **email**: El email de google con el cual nos logeamos, lo usaremos como una llave foranea para obtener los registros de un usuario logeado.
- **username**: Tambien obtenido desde google, lo usaremos para presentacion de datos

**Firestore** nos permite manejar _colecciones_ y _documentos_ muy similar a **mongodb**. Para esta aplicacion nuestra coleccion la llamaremos _scouts_ ; un documento de nuestra coleccion deberia lucir de la siguiente forma:

```json
    {
        "email": "",
        "username": "",
        "phone": "",
        "favorite_phone": "",
        "nightscout_api": "",
        "phones": []
    }
```

Tomando esta vision en consideracion procedemos a acceder con nuestra cuenta de google a firebase.

## Añadiendo Firebase a nuestro proyecto

- Primero ingresa a https://firebase.google.com/
- Haces login con tu cuenta de Google o GSuite
- Click en la parte superior derecha en el boton _Go to console_
- Apareceran una lista de proyectos creados previamente y el boton para crear _Añadir proyecto_. En caso que el proyecto creado previamente para usar Google Auth no aparezca en la lista. Hacemos click en _Añadir proyecto_ y en donde dice _Introduce el nombre de tu proyecto_ deberia aparecer listado. Seleccionarlo y clic en el boton Continuar, Proporcionar los datos adicionales del resto de pasos y click en el boton **Crear proyecto**

Creado el proyeto y dentro de la consola de firebase, hacemos clic en `authentication` y en el tab `sign in method`. Nos aseguramos que la opcion `Google` este habilitada.

Ahora hacemos clic en `Database` y en el `Tab Rules`. Modificamos la regla existende de tal forma que quede de la siguiente manera:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if request.auth.uid != null;
    }
  }
}
```

Esto garantiza que solo olos usuarios que se autentiquen con google podran leer o escribir de nuestra coleccion.

### Conectar el proyecto con el app de Firebase

Una vez creado el proyecto en firebase (o asociado) pasamos a Generar el key desde la Consola de firebase:

- Entrar a https://console.firebase.google.com/ desde el navegador
- Hacer click en _Project Overview > Project configuration_ y seleccionar el tab _Service account_
- Click en la opcion Generate new private key
- Guardamos el archivo (json) en el directorio de nuestra aplicacion. Es posible renombrar el archivo como deseemos, Por ejemplo: super_private_ley.json

El siguiente paso es agregar el nombre de nuestro private key file renombrado a nuestro `.env`, Al final del archivo añadir la linea siguiente:

```ruby
FIREBASE_PRIVATE_KEY="./super_private_ley.json"
```

Con estos preparativos iniciales estamos listos para conectar nuestra aplicacion a firebase/firestore. En el caso de datos de consulta de datos en firestore lo ideal en python seria tener una clase que podamos reutilizar en nuestra aplicacion, que nos permita agregar registros, modificar registros o consultar registros (CRUD). De esta forma mantenemos nuestro codigo simple, organizado y sencillo de entender.

Preliminarmente a realizar nuestro codigo, instalamos los modulos de python que nos permitiran realizar estas operaciones (en linux shell):

```sh
pip install firebase-admin
```

 En nuestro editor de codigo procedemos a crear el archivo `models.py` y agregamos las siguientes lineas:

```python
    import firebase_admin, os
    from firebase_admin import credentials
    from firebase_admin import firestore
    from os.path import join, dirname
    from dotenv import load_dotenv
```

Las lineas anteriores indican que modulos estaremos usando en nuestro archivo `models.py`. Entre estos se encuentran `firebase_admin` el cual usaremos para conectarnos a nuestro proyecto de firebase y realizar las operaciones (CRUD) sobre nuestra coleccion de datos _scouts_. Y usaremos `dotenv` para obtener la variable `FIREBASE_PRIVATE_KEY` de nuestro `.env`

En el mismo archivo agregamos las siguientes lineas:

```python
    envpath = join(dirname(__file__),"./.env")
    load_dotenv(envpath)

    credits = credentials.Certificate(os.getenv("FIREBASE_PRIVATE_KEY"))
    firebase_admin.initialize_app(credits)
```

Las primeras dos lineas son bien conocidas ya que las hemos usado anteriormente en el archivo `superdi.py` y nos permiten cargar nuestro __environment__ para extraer el valor de la variable `FIREBASE_PRIVATE_KEY`. Las dos lineas siguientes conectan nuestra aplicacion con firebase usando el private key que generamos anteriormente. `credits = credentials.Certificate(os.getenv("FIREBASE_PRIVATE_KEY"))` extrae el private key del archivo asi como otros datos adicionales y `firebase_admin.initialize_app(credits)` autentica nuestra aplicacion para usar firebase y la inicializa para poder realizar operaciones.

Definida la conexion con firebase, pasaremos a definir la case model. Normalmente cuando usamos tecnologias como `SQLAlchemy` para trabajar con `flask` y `sqlite`, los modelos son clases en donde definimos distintos atributos que son los campos de la base de datos y usamos un conjunto de funciones nativas del modelo para hacer operaciones sobre la base de datos.

En nuestro caso crearemos la clase `model` como una clase puente que nos permitira usar los metodos de  `firestore` para hacer operaciones sobre base de datos. En otras palabras _model_ funcionara como parent class de la cual heredaran otras clases para returlizar sus metodos. A continuacion agregamos el codigo al final del archivo `models.py`:

```python
    class model:
        def __init__(self,key):
            self.key = key
            self.db = firestore.client()
            self.collection = self.db.collection(self.key)
        def get_by(self, field, value):
            docs = list(self.collection.where(field,u'==',u'{0}'.format(value)).stream())
            item = None
            if docs != None:
                if len(docs) > 0:
                    item = docs[0].to_dict()
                    item['id'] = docs[0].id
            return item
        def get_all(self):
            docs = self.collection.stream()
            items = []
            for doc in docs:
                item = None
                item = doc.to_dict()
                item['id'] = doc.id
                items.append(item)
            if len(items) > 0:
                return items
            else:
                return None
        def add(self, data, id=None):
            if id == None:
                self.collection.add(data)
            else:
                self.collection.document(u'{0}'.format(id)).set(data)
            return True
        def update(self, data, id):
            if id != None:
                if data != None:
                    doc = self.collection.document(u'{id}'.format(id=id))
                    doc.update(data)
            return False
```

Dentro de la clase model iniciamos definiendo nuestro constructor. El cual aceptara el parametro `key` representando el nombre de la coleccion dentro de firestore. El costructor tambien inicializa el cliente de firestore `self.db = firestore.client()` y la coleccion `self.db.collection(self.key)`

El metodo `get_by` recibe el nombre del campo y el valor por el cual queremos filtrar datos de nuestra coleccion. la linea `docs = list(self.collection.where(field,u'==',u'{0}'.format(value)).stream())` ejecuta una consulta a nuestra coleccion de firebase `self.collection` es una referencia a esta coleccion definida en el constructor. Sobre nuestro collection usamos el metodo `where` para filtrar por campo y valor. Prestar especial atencion al caracter u'', esto indicara que python enviara el nombre del campo y el valor con formato `unicode`. Al usar el fragmento de codigo `u'{0}'.format(value)` le estamos diciendo a python que todo valor sin importar de que tipo sea, lo formatee a `unicode`. El metodo `stream` a su vez nos devuelve el flujo de documentos en un tipo de dato especial por lo cual se usa la funcion `list` para convertirlo en un arreglo que pueda ser recorrido desde python.

Normalmente al hacer una consulta a firestore para obtener datos de una coleccion. Por cada registro de la coleccion obtendremos un objeto con dos atributos el id del documento y el metodo `to_dict()` que nos formatea el documento al tipo de dato `dictionary` de python (un formato que tiene una estructura similar a json y que nos hace sencillo acceder a cada campo).

La funcion get_by evalua si el documento existe, en caso que exista crea un item consolidado, es decir con `item = docs[0].to_dict()` almacena el documento en una variable y con `item['id'] = docs[0].id` agregamos el id al documento para tener toda la informacion completa a nuestra disposicion. Otro detalle importante es que **get_by** retorna el primer documento encontrado. Esto lo dejamos asi dado que en nuestro caso Una vez que nuestro usuario se logee con google solo tendra acceso a un documento el cual contendra sus datos (uno y solo uno).

Definimos el metodo get_all el cual no recibe ningun parametro y cuya funcion es obtener todos los documentos de una coleccion, consolidar los documentos creando un diccionary por cada item e ir llenando un arreglo con cada documento consolidado. Esta funcion devuelve un arreglo de todos los documentos de la coleccion o `None` en caso que no hayan documentos.

El metodo `add` recibe los parametros _data_ y _id_. El parametro _id_ es opcional pero en caso de que exista nos permite agregar un _nuevo documento_ con un id definido. En caso que el parametro _id_ no exista el nuevo documento sera creado con un id generado automaticamente por firestore. Ahora bien el parametro _data_ debe ser de tipo `dictionary` y contendra los datos que querramos agregar a nuestra coleccion. 

Para finalizar definimos el metodo `update`, el cual recibe los parametros _data_ e _id_, ambos son requeridos. Mientras _data_ contiene un dict indicando que campos seran alterados con que valores, _id_ define que documento de la coleccion estaremos modificando.

A continuacion agregaremos la clase scout. El proposito de esta clase es actuar como una interface que nos permita pasar los datos de nuestra coleccion scouts de manera mas directa sin pensar en formateos innecesarios al momento de agregar nuevos documentos. Al final del archivo de models agregamos:

```python
    class scout:
        def __init__(self, email = '', username = '', nightscout_api = '', phone = '', favorite_phone = '', phones = []):
            self.email = email
            self.username = username
            self.nightscout_api = nightscout_api
            self.phone = phone
            self.favorite_phone = favorite_phone
            self.phones = phones
```

**Nota:** Mas adelante abordaremos la manera en que usaremos esta clase.

Para finalizar agregaremos la clase `scouts` que hereda de la clase `model` para reutillizar sus metodos y a su vez tiene sus propios metodos para interactuar con la coleccion de scouts. Añadimos el codigo al final del archivo `models.py`:

```python
    class scouts(model):
        def __init__(self):
            super().__init__(u'scouts')
        def get_by_email(self, email):
            docs = list(self.collection.where(u'email',u'==',u'{0}'.format(email)).stream())
            item = None
            if docs != None:
                if len(docs) > 0:
                    item = docs[0].to_dict()
                    item['id'] = docs[0].id
            return item
        def getby_personal_phone(self,phone):
            return self.get_by(u'phone',phone)
        def add(self, data, id = None):
            if type(data) is scout:
                super().add(data.__dict__,id)
            else:
                super().add(data,id)
```

La clase scouts hereda de model, en su constructor llamamos al constructor padre y le pasamos `scouts` que no es mas que el key que espera el constructor de `model` para referenciar una coleccion en firebase.

Despues encontramos el metodo `get_by_email`, el cual obtiene el primer documento de la coleccion `scouts` que coincida con el email proporcionado. Este metodo servira para obtener los datos de nightscout de cada usuario conectado usando una cuenta de google.

El metodo `getby_personal_phone`, recibe como parametro phone (el telefono personal del usuario) y nos devolvera el documento asociado a ese dato. Este metodo llama al metodo `get_by` de la clase `model` y nos sera de mucha utilidad para obtener datos del usuario cuando estemos ejecutando el `events webhook` de `nexmo`.

Para finalizar tenemos el metodo `add`, en el caso que _data_ sea una instancia de la clase `scout` convertiremos sus atributos a dictionary con `data.__dict__`. El atributo _id_ es opcional para este metodo. Prestar atencion que este metodo llama a su vez al metodo `add` de la clase model para su reutilizacion. 

Una vez agregado los datos guardamos el archivo

### Jugando con python console

Una forma muy practica de testear lo que hemos realizado es con la consola de python, previamente abrir la consola de firebase en el navegador y hacer clic en la opcion Database. Asegurarnos de seleccionar **Cloud firestore** en la parte superior izquierda junto al titulo **Database**.

Estando dentro del directorio de nuestro proyecto, desde la terminal de linux ejecutamos el comando `python` esto nos llevara a la consola de python donde podemos ejecutar codigo python. Dentro de la consola de python ejecutamos los siguientes comandos

- Importar nuestro modulo python creado previamente

    ```python
    >>> import models
    >>> from models import model, scouts, scout
    ```

- Crear una instancia de la clase scouts llamada `scout_firebase` y agregar un documento a firebase. Revisar la consola de firebase despues de ejecutar el metodo `add`, en firestore se agregara un nuevo documento con los datos proporcionados. Prestar especial atencion al metodo add, le pasamos una instancia de la clase `scout` con todos los datos correspondientes. Internamente el metodo `add` convierte la instancia de la clase a dictionary.

    ```python
    >>> scouts_firebase = scouts() 
    >>> scouts_firebase.add(scout(email='email@gmail.com', nightscout_api='someurl', phone='12345678', favorite_phone='23456789', phones=['34567890']))
    ```
- Obtener todos los documentos de nuestro `scouts` collection

    ```python
    >>> docs = scouts_firebase.get_all()
    >>> print(docs)
    ```

- Actualizar el documento que agregamos (en este caso solo actualizamos el campo nightscout_api), podemos comprobar la actualizacion el la consola de firebase. Posteriormente obtenemos el documento usando el metodo get_by_email e imprimimos item para confirmar que en efecto se actualizo el valor del campo.

    ```python
    >>> scouts_firebase.update({u'nightscout_api':'some_testing_url'},docs[0]['id'])
    >>> item = scouts_firebase.get_by_email('email@gmail.com')
    >>> print(item)
    ```

Para cerrar la consola de python ejecutamos `quit()` y estaremos de regreso en linux terminal.

### Crear la interface de configuracion de los datos del usuario

Con los modelos de datos definidos, el siguiente paso es crear la interface que recibira los datos del usuario conectado usando google auth, y nuestra aplicacion se encargara de usar el modelo para almacenar esta informacion.

En nuestro archivo `superdi.py`, justo bajo el ultimo `import` realizado agregamos las siguientes lineas:

```python

.....

import models
from models import model, scouts, scout

.....

```

De esta forma agregamos nuestro modulo `models` al script `superdi.py` e importamos del modulo las clases models, scouts y scout para poder usarlas. Posteriormente, antes de la lineas que define la funcion `get_session` agregamos el codigo que inicializa la clase `scouts`

```python

.........


nightscouts = scouts()

def get_session(key):

.........

```

Acontinuacion, pasamos a editar nuestra funcion home, la misma que controla el endpoint `/`. Se modificara la funcion pensando en el worlflow siguiente: Un usuario se autentica con google auth a nuestra aplicacion; Si se esta autenticando por primera vez cuando se cargue `/` se le presentara un form vacio con un flag `new` para indicarle a la aplicacion que el usuario insertara un nuevo documento a firebase. Si por el contrario el usuario que se esta conectando existe previamente al cargar `/` se hara una consulta a firebase para traer los datos relacionados con ese correo y la informacion se mostrara en el formulario con el flag `edit` para indicar a la aplicacion que al enviar el formulario se estara modificando el documento de un usuario existente.

Actualmente nuestro home se encuentra definido de la siguiente forma:

```python
@app.route('/',methods=['GET','POST'])
    def home():
        if get_session("user") != None:
            return render_template("home.html", user = get_session("user"))
        else:
            return render_template("login.html", client_id=os.getenv("GOOGLE_CLIENT_ID"), site_url=os.getenv("SITE_URL"))
```

Con el codigo adicional deberia quedar de esta manera:

```python
@app.route('/',methods=['GET','POST'])
    def home():
        global scouts
        if get_session("user") != None:
            if request.method == "POST":
                phones = request.form.getlist('phones[]')
                if request.form.get("cmd") == "new":
                    nightscouts.add(scout(email=get_session("user")["email"], username=get_session("user")["username"], nightscout_api=request.form.get('nightscout_api'), phone=request.form.get('phone'), favorite_phone=request.form.get('favorite_phone'), phones=phones))
                else:
                    nightscouts.update({u'nightscout_api':request.form.get('nightscout_api'), u'phone':request.form.get('phone'), u'favorite_phone':request.form.get('favorite_phone'),u'phones':phones},request.form.get('id'))
            return render_template("home.html", user = get_session("user"), scout = nightscouts.get_by_email(get_session("user")["email"]))
        else:
            return render_template("login.html", client_id=os.getenv("GOOGLE_CLIENT_ID"), site_url=os.getenv("SITE_URL"))
```

Basicamente se agrego la condicional que evalua si el metodo con el que se esta accediendo a `/` es `POST`. Si es asi por lo general se considera que la peticion ha sido realizada desde un formlulario. 

En este caso estariamos hablando del form de configuracion del usuario. Si el metodo empleado es post se pregunta si el flag, en este caso `cmd` es `new`. De ser asi el metodo `add` sera ejecutado agregando el nuevo documento del usuario. 
**Observacion:** `email` y `username` los obtenemos directamente del session ya que son datos obtenidos desde la autenticacion de google.

En caso de que el flag detectado sea `edit` se recepcionan los nuevos valores del form y se procede a ejecutar el metodo `update` de la clase `scouts` para actualizar el documento del usuario conectado.
**Observacion:** `email` y `username` no son modificados ya que son datos exclusivos de google.

Independeientemente del metodo empleado, en `render_template` pasamos todos los datos del usuario conectado usando la variable  `scout = nightscouts.get_by_email(get_session("user")["email"])`, para llenar el form con la informacion de configuracion en caso que el usuario exista. Los campos del formulario estaran vacios. 

Ahora bien, editamos el archivo `home.html`, este template de jinja es cargado solo si el usuario se ha logeado previamente. Actualmente solo tenemos una linea de codigo dentro de `block content` indicando el usuario conectado y el enlace para logout. Justo bajo esta agregaremos el codigo que recepcionara los datos de la aplicacion para el usuario

El bloque quedaria de la siguiente forma:

```html
    {% block content %}
    <div id="user" class="logged">you are logged in as <b>{{ user.username }}</b> - <a id="logout" class="teal-text" href="/logout">Logout</a></div>
    <div class="row">
    <div class="col s8 offset-s2">
        <div class="card blue-grey darken-1">
        <div class="card-content white-text">
        <h1 class="card-title">Your Scout Profile</h1>
        <div class="row">
        <form id="scout-form" class="col s12" method="POST" action="/">
            <input type="hidden" name="cmd" value="{{ 'new' if scout == None else 'edit' }}"/>
            {% if scout!=None %}
            <input type="hidden" name="id" value="{{ scout.id }}"/>
            {% endif %}
            <div class="row">
            <div class="col s12 input-field">
            <input placeholder="E.g. https://domain.ext/api/v1/entries.json" value="{{ scout.nightscout_api }}" id="nightscout_api" name="nightscout_api" type="text" class="validate" required>
            <label for="nightscout_api" class="white-text">Enter NightScout Api Entries Url (Entries url finish with <b>entries.json</b>)</label>
            </div>
            </div>
            <div class="row">
            <div class="col s12 input-field">
            <i class="material-icons prefix">phone</i>
            <input placeholder="E.g. 50588888888" id="phone" name="phone" value="{{ scout.phone }}" type="tel" class="validate" pattern="[0-9]+" required>
            <label for="phone" class="white-text">Your Phone Number</label>
            </div>
            </div>
            <div class="row">
            <div class="col s12 input-field">
            <i class="material-icons prefix">phone</i>
            <input placeholder="E.g. 50588888888" id="favorite_phone" name="favorite_phone" value="{{ scout.favorite_phone }}" type="tel" class="validate" pattern="[0-9]+" required>
            <label for="favorite_phone" class="white-text">Emergency Contact</label>
            </div>
            </div>
            <div class="row">
            <div class="col s12 add-contacts-container">
            <div class="row">
            <div class="col s6">
                <label class="white-text">Add 5 additional contact numbers:</label>
            </div>
            <div class="col s6 add_contact">
                <div class="right-align"><a onclick="add_contact()" class="btn waves-effect waves-light red"><i class="material-icons">group_add</i></a></div><br/>
            </div>
            </div>
            <div class="divider"></div>
            <div class="contact_numbers" id="contact_numbers">
            </div>
            </div>
            </div>
            <div class="row">
            <div class="col s12 right-align">
            <button class="waves-effect waves-light btn-small" type="submit"><i class="material-icons left">save</i> Save</button>
            </div>
            </div>
        </form>
        </div>
        </div>
        </div>
    </div>
    </div>
    {% endblock %}
```

Algunas observaciones sobre el formulario, si la variable _scout_ es `None` el flag `cmd` tendra el valor `new` caso contrario `edit`. Los values de los campos de texto reciben `{{ scout.phone }}`, por ende cuando scout es `None` jinja imprimira vacio. Cuando scout existe el id se recepciona en un campo tipo hidden, este campo no debe ser modificado ya que se trata del identificador unico del documento en firebase. La funcion `add_contact()` de javascript no esta definida.

Siempre en el archivo `home.html` despues de `{% endblock %}` agregamos el siguiente bloque de codigo. En este caso usaremos el bloque `script` que definimos en `layout.html` para definir las funciones necesarias de javascript.

```javascript
{% block script %}
 <script language="javascript">
 var contacts_numbers = null;
 var container = null;
 var incremental = 0;
 window.addEventListener('load', function(event){

   container = document.getElementById("contact_numbers");
   contact_numbers = container.getElementsByClassName("contact_number");

   var phones = validate({{ scout.phones|safe }});
   //var phones = {{ scout.phones|safe if scout else "Array()" }};
   for(var p=0;p<phones.length;p++){
    add_contact(phones[0]);
   }

 });
 function validate(value){
  if(value!==null & value!==undefined)
   return value;
  else
   return Array();
 }

 function add_contact(value){
  if(contact_numbers.length < 5){
   incremental += 1;
   var div = document.createElement("div");
   div.className = 'row contact_number';
   div.setAttribute('id','id_'+incremental);
   if(!(value!=null && value!==undefined)){
    value = "";
   }
   div.innerHTML += '<div class="col s12 input-field"><i class="material-icons prefix">contact_phone</i><input placeholder="E.g. 50588888888" name="phones[]" value="'+value+'" type="tel" class="validate" pattern="[0-9]+"><i class="material-icons prefix sufix delete" onclick="delete_contact(\'id_'+incremental+'\')">delete</i></div>';
   container.appendChild(div);
   contact_numbers = container.getElementsByClassName("contact_number");
  }else{
   M.toast({html: 'Sorry, You can just add a maximun of 5 contact numbers'});
  }
 }

 function delete_contact(id){
  contact_number = document.getElementById(id);
  container.removeChild(contact_number);
 }

 </script>
{% endblock %}
```

En el bloque `script` definimos tres funciones y el event listener de `onload` page. La funcion `validate` que evalua si el valor de `{{ scout.phones|safe }}` pasado por jinja es vacio de ser asi validate retorna un `Array()` vacio, en caso contrario se retora el arreglo de phones obtenido por jinja.

Mas adelante definimos la funcion `add_contact()`, esta funcion agregara de forma dinamica un campo de texto en donde el usuario podra digitar un numero telefonico adicional de los 5 permitidos, al lado de cada input aparecera el icono de eliminacion input en particular. Esta misma funcion evalua si se ha alcanzado el numero de contactos permitidos, en ese caso se usa `M.toast` de materialize para desplegar una alerta al usuario indicando que no puede agregar mas de 5 numeros. Esta funcion es desencadenada al momento de cargar la `/` y al momento de hacer clic en el boton de agregar numeros telefonicos.

La funcion `delete_contact()` elimina el registro creado por `add_contact()`. La funcion se desencadena desde el evento `onclick` del icono de eliminacion agregado  por `add_contact` para cada input phone. 

Hecho esto analizamos el eventListener creado para `onload` page. Al momento de cargarse `/` se usa la funcion validate para evaluar si el valor `{{ scout.phones|safe }}` esta vacio (cuando se esta agregando un nuevo registro o cuando el usuario no ha agregado ningun phone), de ser asi validate devuelve un arreglo de javascript vacio ya que jinja no imprimia nada. 
En caso de que phones tenga datos `{{ scout.phones|safe }}` devolvera un arreglo manejable desde javascript. Adicionalmente a esto, despues encontramos el comentario `var phones = {{ scout.phones|safe if scout else "Array()" }};` este metodo nos dice que si jinja nos de el arreglo en caso de que scout exista, en caso contrario que imprima un arreglo vacio. Este metodo tambien es valido para manipular datos pasados desde jinja a javascript.
Si al cargar la pagina, phones contiene informacion la funcion `add_contact` se ejecuta por cada posicion del arreglo de phones, pasando el valor del phone para que lo ubique en el atributo value del input.

Con estos ultimos detalles hemos concluido el flujo de configuracion de datos usando login de google auth y firebase/firestore para almacenamiento y lectura de los mismos.

En este punto deberiamos ser capaces de logearnos con google usando la aplicacion, de agregar nuestra configuracion de nightscout desde el formulario, guardar nuestros datos en firestore, de modificar nuestra configuracion y de deslogearnos correctamente.

# 3. Configuracion de Aplicacion en Nexmo y Creacion de Scheduler en Python para el envio de alertas de Nightscout

En el apartado anterior concluimos con la parte de nuestra aplicacion en donde el usuario podra agregar, editar y consultar sus configuraciones desde una UI creada en flask con jinja usando google auth para la autenticacion y firebase/firestore para almacenamiento de los datos.

A partir de ahora nos centraremos en la creacion de un hilo que corra de manera independiente ejecutar una funcion con una frecuencia dada para hacer un `call`  a aquellos numeros de usuario cuyo nivel de glucosa en la sangre se encuentre fuera del rango 70 a 240. En caso que el usuario no responda, la aplicacion debera proceder a enviar `sms` al numero favorito registrado por el usuario y a otros numeros adicionales para alertarlos del nivel de glucosa del usuario. Si pasado un tiempo prudencial el nivel de glucosa sigue fuera del rango permitido la aplicacion repite el proceso. 

Otro caso de uso contemplado es que si el `nightscout_url` no responde despues de 1h, la aplicacion debe enviar un `sms` indicando al usuario que su servicio de nightscout tiene problemas.

Para lograr esto usaremos Nexmo, una plataforma de comunicaciones que cuenta con una gran variedad de APIs para ejecutar servicios de comunicacion usando diversos canales. Nexmo es muy conveniente para programar las funcionalidades expuestas anteriormente. Para encontrar mas informacion sobre los APIs y SDKs disponibles en esta plataforma revisar el link https://developer.nexmo.com/

## Creacion de una cuenta en Nexmo

- Hacer clic sobre el link https://dashboard.nexmo.com/sign-up 

- Introducimos nuestros datos y hacemos clic en el boton `Create my free account`

- Activar la cuenta  de nexmo haciendo clic en el enlace enviado por nexmo a nuestro email. Tendremos que digitar nuestro numero de celular para recibir un verification code con el cual podremos activar la cuenta, una vez hecho esto quedara activa y lista para usarse. 

 **Nota**: Un detalle adicional y muy importante es que esta cuenta es __free__ y tiene saldo basico para realizar pruebas con `Voice API` y `SMS`. Sin embargo este saldo estara limitado a hacer outbound calls y sms, para poder controlar el flujo de llamadas `inbound` (Llamadas entrantes hechas por el cliente) es necesario habra que hacer upgrade la cuenta para comprar un `NEXMO VIRTUAL NUMBER` al que se pueda hacer tracking usando los `Event Webhooks`. Lo ideal (pero no necesario para esta aplicacion) es hacer el upgrade de nuestra cuenta en nexmo y tener un virtual number asignado para tener acceso ilimitado a todas las funciones de Nexmo.

- Una vez dentro de la cuenta de `Nexmo` el dashboard nos presentara dos datos que son muy importantes para nuestra aplicacion **_apikey_** y el **_apisecret_** copiamos esos valores y en nuestro `.env` los agregamos de la siguiente forma

    ```ruby
    NEXMO_API_KEY="NEXMO_API_KEY"
    NEXMO_API_SECRET="NEXMO_API_SECRET"
    ```

 Reemplazamos los valores `NEXMO_API_KEY` y `NEXMO_API_SECRET` por los correspondientes y guardamos el archivo

### Crear una aplicacion en Nexmo

Como mencionamos anteriomente, para alcanzar nuestro objetivo necesitamos `VOICE API` (https://developer.nexmo.com/voice/voice-api/overview) y `MESSAGES API` (https://developer.nexmo.com/messages/overview) para hacer llamadas y recibir mensajes respectivamente. En el caso de el envio de mensajes usando `MESSAGES API` basta usar el `api_key` y el `api_secret`. Sin embargo, para usar el `VOICE API` se necesita el `APPLICATION_ID` y el `PRIVATE_KEY` de la aplicacion para poder generar un JWT (Java Web Token) credenciales que verifican nuestra identidad y garantizan el intercambio transparente de mensajes entre nuestra aplicacion y la aplicacion de Nexmo que soportara `Voice` para la realizacion de llamadas.

En otras palabras, tendremos que crear una aplicacion de Nexmo con `VOICE API` y `MESSAGES API` habilitados.

- En el sidebar de Nexmo hacer clic en el link `Your applications`. Se cargara un card list con nuestras aplicaciones y la opcion de agregar una aplicacion nueva.

- Clic en el boton `Create a New Application`.

- Introducimos los datos de la aplicacion: Nombre de la aplicacion

- Habilitamos `Voice`: El seleccionar Voice la aplicacion solicitara webhooks urls: event url, Answer Url y Fallback Answer url
  
  - **Event url**: es la url de nuestro server, a la cual nexmo enviara el tracking de todos los eventos que ocurran en nuestro voice API. Por ejemplo al realizar una llamada, nexmo enviara cada uno de los status de la llamada ringing, answered, unanswered y complete. Para la aplicacion que estamos realizando esto es fundamental ya que necesitamos conocer el estado de la llamada realizada a un usuario ya que una de nuestras condiciones es que si el usuario no responde `unanswered` se envian `sms` a otros numero registrados por el usuario. En este campo se asignara un valor similar a `https://domain.ext/events` donde `domain.ext` es el dominio en donde nuestra aplicacion sera desplegada

  - **Answer url**: se asigna para `inbound` calls de nexmo. Por ejemplo cuando un cliente hace una llamada a un `Nexmo virtual Number` nexmo automaticamente conecta la llamada al answer url (que tambien estara definida en nuestro server) y la misma devuelve un NCCO (Nexmo call control object) que define el flujo de la llamada. Mas informacion sobre NCCO en https://developer.nexmo.com/voice/voice-api/ncco-reference. En el caso de nuestra aplicacion no es tan necesario definir un answer url ya que estaremos pasando nuestro NCCO directamente en la funcion `create_call` de `VOICE_API`. Sin embargo, para definir un valor el mismo deberia ser similar a `https://domain.ext/answer` donde domain.ext es el dominio en donde nuestra aplicacion sera desplegada

  - **Fallback answer url**: En caso que por alguna razon el `inbound` call no pueda ser realizado, la llamada se redirije al `Fallback answer url`, que normalmente es un NCCO respondiendo al usuario que ha habido un problema y que la llamada no pudo ser establecida. En nuestro caso no aplica, por que estamos usando `outbound` calls. Asi que de momento podemos dejar el campo vacio

- Habilitar `Messages`: En caso de messages se solicitan dos urls:

  - **inbound url**: Es posible conectar nuestra aplicacion de Messages con nexmo con otras aplicaciones. Por ejemplo el `Facebook Messenger` de una pagina de facebook. Si un usuario envia un mensaje al messenger de una pagina de facebook conectado al App de nexmo, el mensaje es recibido a traves del `inbound` url en donde podemos manipular e incluso almacenarlo en una base de datos. Los datos indican que tipo de canal se uso, el usuario que lo envio y el mensaje enviado.

  - **status url**: El proposito de este campo es bastante similar al **Event url**, solamente que en este caso el server hara tracking de los status de los mensajes. Si el mensaje fue entregado e incluso si el mismo fue leido por el usuario.

  Ambos urls tendran nomenclaturas muy similares a las anteriores, por ejemplo: `https://domain.ext/inbound` y  `https://domain.ext/status`. Sin embargo, para esta aplicacion no es necesario configurar ninguna de ellas ya que lo que se usara es envio de outbound `sms` usando messages api.

De todo lo anterior mencionado el unico `Webhook` que necesitamos definir es el `event url` del `VOICE API`.

Para finalizar hacemos clic en el Boton `Generate new application` 

Agregada nuestra aplicacion en el apartado anterior, entramos a la vista de detalles de la aplicacion. En caso que hayamos hecho upgrade a nuestra cuenta podremos ver el boton `Buy new numbers`. Desde este boton es posible enlazar un numero virtual de Nexmo a nuestra aplicacion para que los outbounds call no aparezcan como numeros desconocidos. Si este es nuestro caso compramos el numero y posteriormente lo linkeamos a nuestra aplicacion.

Con esto hemos concluido con la creacion de nuestra aplicacion de Nexmo. Ahora procedemos a obtener el  `APPLICATION_ID` y el `PRIVATE_KEY`. Entramos a la vista de detalle de la aplicacion en Nexmo y en la parte superior izquierda de la vista se mostrara el application id. 

Para el `PRIVATE_KEY`, siempre en la vista de detalle de la aplicacion hacemos clic en el boton `Edit` y click sobre el boton `Generate public and private key`. Nexmo descarga un archivo por nosotros el cual contiene la clave privada. Movemos el archivo generado al directorio de nuestra aplicacion, podemos renombrarlo a `nexmo_private.key` por ejemplo.

### Funciones para el envio de Notificaciones con Nexmo

Regresamos al editor de codigo, editamos una vez mas nuestro `.env` y agregamos las siguientes lineas:

```ruby
NEXMO_APPLICATION_ID="NEXMO_APPLICATION_ID"
NEXMO_PRIVATE_KEY="./NEXMO_PRIVATE_KEY.key"
NEXMO_NUMBER="NEXMO_VIRTUAL_NUMBER"
```

Recordar reemplazar los valores `NEXMO_APPLICATION_ID`, `./NEXMO_PRIVATE_KEY.key` y `NEXMO_VIRTUAL_NUMBER` por sus correspondientes. En caso que no tengamos `NEXMO_VIRTUAL_NUMBER` podemos usar el valor `Nexmo` de momento.

Nuestra aplicacion realizara ping al nighscout de un usuario cada minuto y obtendra el nivel de glucosa de un usuario. En caso que este nivel de glucosa no este en el rango permitido, la aplicacion llamara al usuario indicando el nivel de glucosa. Sin embargo si se deja de esta forma y el nivel de glucosa se mantiene fuera de rango por un periodo de tiempo considerable la llamada se realizara cada minuto, por esa razon estableceremos una variable adicional llamada `WAIT_AFTER_CALL` para controlar ese aspecto. Otra variable que definiremos es `NEXMO_FAILED_PING_SMS` que controlara el numero de pings fallidos para el nightscout de un usuario, el numero por defecto sera `60` (equivalente a 1 hr) considerando que cada ping se hara cada minuto. En caso que el numero de pings fallidos alcance este valor se enviara un `sms` al usuario para que revice ese servicio.

En nuestro `.env` insertamos al final del archivo:

```ruby
WAIT_AFTER_CALL="120"
NEXMO_FAILED_PING_SMS="60"
```

Haciendo un inventario de los modulos que necesitamos para desarrollar esta parte de la aplicacion. Necesitamos crear un Thread para ejecutar nuestro job, Python cuenta con `Thread` y tambien esta `multiprocessing` ambos nativos. Realizaremos algunos request para obtener informacion de nightscout api y para usar el messages api de `Nexmo` con el fin de enviar `sms`, podemos usar el modulo `requests` (instalado previamente)
De ser posible un scheduler que nos permita ejecutar una funcion periodicamente y que corra en el `Thread` que creemos con `multiprocessing`. Para ello podriamos intalar el modulo `schedule` y logicamrente usaremos el modulo de `Nexmo` para python que nos permitira usar `VOICE API` al conectarse a nuestro Nexmo Application.

Desde la consola de linux ejecutamos el siguiente comando:

```sh
pip install nexmo schedule
```

Editamos el archivo `superdi.py`, despues del ultimo modulo importado agregamos el codigo:

```python

import nexmo, schedule, time, signal, uuid

from multiprocessing import Process

```

Adicionalmente usaremos los modulos nativos `signal` para la deteccion de SIGTERM (CRTL+C) usado para la terminacion de la aplicacion desde la consola, `uuid` para la generacion de un identificador unico para nuestro proceso corriendo en el `Thread` y logicamente la 

En el mismo archivo, antes de la definicion de la funcion `get_session` agregamos las lineas:

```python

............

client = nexmo.Client(
    application_id = os.getenv('NEXMO_APPLICATION_ID'),
    private_key = os.getenv('NEXMO_PRIVATE_KEY')
)

active_scouts = nightscouts.get_all()

.............

def get_session(key):
```

Con la linea `client = nexmo.Client` inicializamos el cliente de Nexmo, como estaremos usando `VOICE API` los valores que estaremos pasando son nuestro `NEXMO_APPLICATION_ID` y el `NEXMO_PRIVATE_KEY`. Ambos los tenemos almacenados en nuestras variables de entorno, asi que simplemente obtenemos los valores de las mismas usando `os.getenv` como lo hemos venido haciendo hasta ahora.

La linea que sigue a continuacion `active_scouts = nightscouts.get_all()` obtiene la lista completa de los usuarios registrados hasta el momento. Esta lista sera actualizada cada hora para detectar cambios realizados por el cliente desde el `user interface` que creamos con anterioridad.

Siempre en `superdi.py`, despues de la definicion del endpoint `/logout`. Agregaremos las funciones encargadas de las notificaciones a los usuarios. Iniciaremos con la funcion que hace notificacion al usuario indicando que el servicio de nightscout no esta respondiendo, para ello usaremos el `MESSAGES API` ya que estaremos enviando un `sms`:

```python
nightscout_failed_pings = {}
def handle_nightscout_failed_pings(to,api_url,username):
    global client
    global nightscout_failed_pings
    if to not in nightscout_failed_pings: 
        nightscout_failed_pings[to] = 1
    else:
        nightscout_failed_pings[to] += 1
    #print('Intent: {0} for {1}'.format(nightscout_failed_pings[to],to))
    if nightscout_failed_pings[to] == int(os.getenv("NEXMO_FAILED_PING_SMS")):
        response = requests.post(
            'https://api.nexmo.com/v0.1/messages',
            auth=HTTPBasicAuth(os.getenv("NEXMO_API_KEY"), os.getenv("NEXMO_API_SECRET")),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json={
                "from": {
                    "type": "sms",
                    "number": os.getenv("NEXMO_NUMBER"),
                },
                "to": {
                    "type": "sms",
                    "number": to
                },
                "message":{
                    "content":{
                        "type": "text",
			"text": "Dear {0} the nexmo api url: {1} is not responding, please check the service".format(username,api_url)
                    }
                }
            }
        ).json()

        #Reset the variable
        nightscout_failed_pings[to] = 0

        if "message_uuid" in response:
            return True
    return False
```

Antes de la definicion de la funcion `handle_nightscout_failed_pings`, se encuentra `nightscout_failed_pings = {}` una variable que controlara el numero de pings fallidos por usuario. En este caso el key del objeto (indice) sera el numero de telefono del usuario y el valor el conteo de pings fallidos.

La funcion `handle_nightscout_failed_pings` recibe como parametros `to`, `api_url` y `username`. El parametro `to` es el numero de telefono del usuario, `api_url` es la url del api de nightscout que esta presentando el problema de conexion y `username` es el nombre del usuario al cual sera dirigido el `sms` en caso de que sea necesario.

Inicialmente la funcion evalua si el key `to` se encuentra presente en el objeto `nightscout_failed_pings` , de no ser asi se inicializa el key en el objeto con el valor de _1_. En caso de que exista, el valor aumenta en _1_.

Despues se evalua la condicional `if nightscout_failed_pings[to] == int(os.getenv("NEXMO_FAILED_PING_SMS")):`, indicando si el numero de pings fallidos ha alcanzado el maximo se procede a enviar el `sms` notificando del problema al usuario.

`Messages API` es `BETA`  por esa razon las funciones para python no han sido incorporadas aun a la libreria de `Nexmo` para python. Para hacer el envio del mensaje procedemos a usar requests y usaremos el `url` de `messages api` para hacer nuestra solicitud.

El metodo a utilizar al hacer el request sera `POST`, el primer parametro `https://api.nexmo.com/v0.1/messages` corresponde al url de messages api, como segundo parametro la autenticacion, en este caso estamos usando `MESSAGES API` para enviar `sms`, basta con autenticarnos pasando el `NEXMO_API_KEY` y el `NEXMO_API_SECRET` obtenidos de nuestras variables de entorno. Esto se refleja en `auth=HTTPBasicAuth(os.getenv("NEXMO_API_KEY"), os.getenv("NEXMO_API_SECRET"))`. En el header definimos que los datos seran enviados en formato `JSON`.

El json esta estructurado en tres secciones: `from` en donde se define el canal que usaremos para enviar el mensaje (whatsapp, messenger , sms etc) en nuestro caso logicamente es `sms`, despues se indica  el `number` que representa el numero de telefono del cual enviamos el sms (aca asignamos el valor de la variable de entorno `NEXMO_NUMBER`). En la seccion `to` de igual manera definimos `sms` en el `type` y en `number` asignamos el valor del parametro `to` que recibe nuestra funcion que representa el numero de destino al cual el `sms` sera enviado. La seccion `message`, es donde se indica el tipo de contenido que enviaremos (imagen, video, texto). Como lo que estaremos enviando es una notificacion `type` seria `text` y `text` (mesaje que se enviara) recibe el valor de `Dear {0} the nexmo api url: {1} is not responding, please check the service".format(username,api_url)` en donde `{0}` es reemplazado por el valor de `username` y `{1}` por el valor de `api_url`

Una vez la notificacion es enviada, el conteo de pings fallidos se resetea a `0`. Si en el response devuelto por nexmo existe un `message_uuid` key la funcion retorna `True` indicando que el mensaje se envio. Todo mensaje o llamada realizados por/hacia `Nexmo` tienen su propio `uuid`. En caso que `Nexmo` no haya generado el `message_uuid` la funcion asume que el mensaje no fue enviado y se retorna `False`

Al final de nuestro archivo agregamos la siguiente funcion, que de igual manera enviara el nivel de glucosa del usuario a un numero elegido por el usuario en el _UI_:

```python
def sms_glucose_alert(to, username, glucose):
    global client
    #We send our sms using the messages api not the sms api
    response = requests.post(
        'https://api.nexmo.com/v0.1/messages',
        auth=HTTPBasicAuth(os.getenv("NEXMO_API_KEY"), os.getenv("NEXMO_API_SECRET")),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
	},
        json={
            "from": {
                "type": "sms",
                "number": os.getenv("NEXMO_NUMBER"),
            },
            "to": {
                "type": "sms",
                "number": to
	    },
            "message":{
                "content":{
                    "type": "text",
		    "text": "Alert {username} Blood Glucose is {glucose}".format(username=username, glucose=glucose)
                }
            }
        }
    ).json()

    if "message_uuid" in response:
        return True
    else:
        return False
```

La funcion `sms_glucose_alert` es bastante similar a `handle_nightscout_failed_pings` en el sentido que se usa exactamente el mismo procedimiento para el envio de _sms_. La diferencia radica en que se estara indicando el **nivel de glucosa** en lugar de el url_api. En esta funcion se ha agregado un comentario adicional aclarando que el envio de _sms_ se realizara usando el `MESSAGES API` no el `SMS API`. En efecto existe un `SMS API` que realiza se limita solamente al envio de `sms`, pero es muy posible que en un futuro cercano este API se reemplace por `MESSAGES API` que es mucho mas extendido.

Posteriormente agregamos la funcion `call_glucose_alert`:

```python
last_call = {}
def call_glucose_alert(to, glucose):
    if to in last_call:
        if int(time.time()-last_call[to]) < int(os.getenv("WAIT_AFTER_CALL")):
            print("The number {0} was called recently.. Please wait a little longer: {1}".format(to,int(time.time()-last_call[to])))
            return False
    #print('Call {0} {1}'.format(to, glucose))
    last_call[to] = time.time()
    
    #We make our call using the voice API
    response = client.create_call(
        {
            "to": [{
                "type": "phone",
                "number": to
            }],
            "from": {
                "type": "phone",
                "number": os.getenv('NEXMO_NUMBER')
            },
            "ncco": [
                {
                    "action": "talk",
                    "text": "Alert Your Blood Glucose is {0}".format(glucose)
                }
            ],
            "eventUrl": [
                "{url_root}/webhooks/events".format(url_root=os.getenv("SITE_URL"))
            ]
        }
    )
    if "uuid" in response:
        return True
    else:
        return False
```

Si observamos con cuidado antes de la funcion hemos agregado la variable `last_call` la cual desempeña un papel similar a `nightscout_failed_pings`. `last_call` es un objecto cuyo indice sera el numero de telefono del usuario y el valor del indice sera el tiempo actual. Al inicio de la funcion se evalua si existe el key `to` en `last_call`, de existir evaluamos si el periodo entre el tiempo actual y el tiempo en el que se realizo la ultima llamada de un usuario en particular no ha alcanzado el valor de nuestra variable de entorno `WAIT_AFTER_CALL`, si esta condicional devuelve `True` se imprime un mensaje indicando que se esperara un tiempo adicional ya que el numero fue llamado recientemente y se retorna `False` evitando que se haga el `call`.

En caso que `to` no exista en `last_call` lo inicializamos con el valor `time.time()` que refleja el tiempo actual en segundos, que a su vez es una marca de tiempo que estaremos usando para hacer calculos. Por ejemplo: El tiempo transcurrido en _segundos_ desde la ultima llamada es calculado en `int(time.time()-last_call[to])` y lo comparamos con el valor de `WAIT_AFTER_CALL` cuya unidad de medida es _segundos_. 

Para realizar el `call` usando el `VOICE API` de Nexmo, usaremos la funcion `create_call` del modulo de nexmo para python. Previamente hemos inicializado el cliente de `nexmo` usando el `application_id` y el `private_key` indicando que tenemos todos los preparativos listos para el uso del `VOICE API`.

El metodo `create_call` de `client` recibe como parametro unico un dictionary de python un objecto cuya nomenclatura es muy similar a la de objetos `JSON`, facilitandonos su manipulacion ya que JSON es muy conocido y sencillo de implementar.

Al igual que `MESSAGES API`, la funcion `create_call` tiene las secciones `to` y `from`. La unica variante de estas secciones es el `type` que en este caso sera `phone` indicando que se realizara una llamada. En `from` el valor de `number` sera nuestro `NEXMO_NUMBER` y en `to` asignaremos el parametro `to` que recibe nuestra funcion. 

Posteriormente tenemos la seccion `NCCO`. Un NCCO es un JSON que indica a nexmo el flujo de acciones que se estaran realizando sobre la llamada. Un NCCO puede ser pasado de dos formas a `create_call`: atraves del `answer_url` que seria un endpoint en nuestro server cuya funcion es devolver el NCCO en formato JSON, esto proporciona una gran ventaja al crear aplicacion con workflows extendidos. Ya que desde el server podemos generar NCCO personalizados en dependencia de multiples factores. En el caso de nuestra aplicacion la accion sera reproducir un mensaje al usuario indicando el nivel de glucosa, por esa razon usaremos el segundo metodo que es pasar el `NCCO` como un objeto directamente a nuestro `NCCO` section de `create_call`.

La seccion `NCCO` tiene el key `action` cuyo valor es `talk`. Este action le indica a Nexmo que al realizar la llamada se hara `speech` de un mensaje. Cabe mencionar que `Nexmo` soporta la reproduccion de `speech` en diversos idiomas. Posteriomente tenemos el key `text` en donde se define el texto que deseamos sea reproducido en el `call`. Para mayor informacion sobre NCCO y actions visitar el siguiente link https://developer.nexmo.com/voice/voice-api/ncco-reference

Despues se define el `eventUrl` que es un `webhook` de nexmo para el envio de informacion a nuestro server. EventUrl es un endpoint de nuestro server que estara recibiendo un peticiones desde Nexmo en formato JSON con informacion de los diferentes estados de la llamada. Esto es muy conveniente para nosotros ya que nos interesa capturar el estado `unanswered`, para el envio de nuestros `sms`. Puesto que como hemos mencionado anteriormente si el usuario no responde _sms_ seran enviados al numero favorito y otros numeros adicionales. Para mas informacion sobre status que llegaran al `eventUrl` visitar https://developer.nexmo.com/voice/voice-api/guides/call-flow

Al igual que `MESSAGES API`, en `VOICE API` Nexmo genera un `uuid` unico por cada llamada realizada. En caso que nuestro responde no tenga `uuid` generado la funcion retorna `False` asumiendo que la llamada no pude ser realizada y en caso contrario se retorna `True`

**Nota importante**: La funcion `call_glucose_alert` es el desencadenante inicial del workflow de Nexmo.

A continuacion agregamos nuestro `event` webhook endpoint, al final de nuestro `superdi.py` insertamos el siguiente codigo:

```python
@app.route('/webhooks/events',methods=["POST","GET"])
def events():
    global client
    req = request.get_json()
    #print(req)
    if "status" in req:
        if req["status"] == "unanswered":
            phone = req["to"]
            uscout = nightscouts.getby_personal_phone(phone)
            if uscout!=None:
                entries = requests.get(uscout["nightscout_api"]).json()
                glucose = entries[0]['sgv']
                sms_glucose_alert(uscout["favorite_phone"], uscout["username"],glucose)
                #print('sms simulation to: {0} {1} {2}'.format(uscout["favorite_phone"], uscout["username"], glucose))
                for phone in uscout["phones"]:
                    #print('sms simulation to: {0} {1} {2}'.format(phone, uscout["username"], glucose))
                    sms_glucose_alert(phone, uscout["username"],glucose)
    return "Event Received"
 ```

En caso que el nivel de glucosa del usuario no este dentro del rango permitido se ejecutara la funcion `call_glucose_alert` que realiza una llamada usando `VOICE API` de Nexmo, para indicar el nivel de glucosa en la sangre. Al momento de realizar la llamada nexmo envia informacion a event webhook para informar sobre el estado `started`, cuando el telefono comienza a repicar Nexmo envia informacion a event webhook indicando el estado `ringing` y asi sucesivamente con el resto de los estatus de la llamada. 

Para obtener la informacion que Nexmo envia a nuestro `event webhook` usaremos `req = request.get_json()`, podemos descomentar la linea `print(req)` que sigue a continuacion para analizar la estructura del json usando `gunicorn`.

Como lo que nos interesa evaluar en este caso es el estado de la llamada, hacemos una condicional consultando si `status` existe para `req`. En caso que exista se crea una segunda condicional que evalua si el valor del `status` es `unanswered`. De ser asi capturamos el numero de phone donde la llamada no fue atendida usando `phone = req["to"]` y usamos nuestro model para obtener el registro relacionado con este phone `uscout = nightscouts.getby_personal_phone(phone)`.

Si el registro existe, pasamos a recuperar los ultimos niveles de glucosa para del usuario usando `requests` con el metodo `get`, de la siguiente forma `entries = requests.get(uscout["nightscout_api"]).json()` y de ahi obtenemos el ultimo nivel de glucosa registrado para el usuario `glucose = entries[0]['sgv']` (Nightscout API ordena las entradas de forma descendente por nosotros, lo que indica que el ultimo nivel de glucosa sera el primero). Con el nivel de glucosa obtenido usamos la funcion `sms_glucose_alert` para enviar `sms` indicando el nivel de glucosa del usuario a su numero favorito y otros numeros adicionales registrados por el usuario.

Con esto hemos finalizado la seccion de funciones para el envio de notificaciones

## Usando Scheduler con Python para el envio de notificaciones automaticas

En esta seccion agregaremos las lineas de codigo encargadas de crear un hilo paralelo a la aplicacion de `Flask`, el cual se encargara de ejecutar el `scheduler` que a su vez evaluara los niveles de glucosa de todos los usuarios de la aplicacion y ejecutara la funcion `call_glucose_alert` a aquellos usuarios cuyo nivel de glucosa no se encuentre en el rango permitido. Adicionalmente a esto el scheduler es el encargado de ejecutar la funcion `handle_nightscout_failed_pings` que evaluara el numero de intentos de conexion fallidos al nightscout de un usuario y enviara la notificacion cuando haya alcanzado el numero maximo de intentos permitidos.

En nuestro editor de texto, agregamos al final del archivo `superdi.py` las siguientes lineas:

```python
thread = None

class ApplicationKilledException(Exception):
    pass

#Signal handler
def signal_handler(signum, frame):
    raise ApplicationKilledException("Killing signal detected")

```
En las lineas anteriores definimos algunas funciones y variables. `thread` es la variable que asignaremos a nuestro hilo paralelo, `ApplicationKilledException` es una clase personalizada que hereda de `Exception`, creada por nosotros con la unica funcion de desencadenarse cuando la funcion `signal_handler` es ejecutada. Despues viene la definicion de la funcion `signal_handler` que desencadena nuestra `Exception` personalizado. La idea de `signal_handler` es darnos un poco de control al momento en que el proceso sea detenido por intervencion humana (haciendo CTROL+C) o con el comando kill.

Al tener mayor control podremos ejecutar ciertas operaciones adicionales para detener nuestro scheduler correctamente.

```python
def refresh_scouts(id):
    global active_scouts
    active_scouts = nightscouts.get_all()
    print("Refresh Scouts Job " + id+ "")
```

`refresh_scouts` es una funcion que actualiza el valor de la variable `active_scouts` durante el ciclo de vida de nuestra aplicacion. La misma sera ejecutada por un segundo scheduler dentro de nuestro `Thread` cada hora. El proposito de esta funcion mantener informacion reciente de nuestra coleccion de `scouts` de firebase. De esa forma si un usuario ha realizado cambios usando la interface de usuario, estos cambios estarian disponibles en cuando `refresh_scouts` sea ejecutada. 

Otro detalle interesante es que recibe el parametro `id`, esto es debido a que scheduler al ejecutar un job tendra que identificarlo con un `id` unico, con la finalidad de poder editar la configuracion de ejecucion de un job en tiempo real o bien para matar un job en particular.

Procedemos a agregar las siguientes lineas de codigo al final de nuestro archivo `superdi.py`:

```python
def job(id):
    #Calling nemo global client variable
    global client
    global active_scouts
    print("Alerts Job " + id+ "")
    if active_scouts != None:
        for active_scout in active_scouts:
            #print(active_scout["nightscout_api"])
            try:
                entries = requests.get(active_scout["nightscout_api"]).json()
                glucose = entries[0]['sgv']
                #We add a dynamic attribute called glucose to pass glucose info to events url
                if 70 <= glucose <= 240:
                    print("{0} is inside the range for {1}".format(glucose,active_scout["username"]))
                else:
                    print("Executing emergency call and loading sms NCCO if needed")
                    call_glucose_alert(active_scout["phone"],glucose)
            except:
                handle_nightscout_failed_pings(active_scout["phone"],active_scout["nightscout_api"],active_scout["username"])
                print("Server could not establish connection with "+active_scout["nightscout_api"])
    
```

La funcion `job` sera nuestro job principal, la funcion se ejecutara cada minuto por scheduler. Inicia leyendo la variable `active_scouts`, la misma que sera actualizada cada hora usando la funcion `refresh_scouts`. Procede a evaluar cada uno de los usuarios usando `for active_scout in active_scouts:`.

Dentro de `try` ubicamos el `requests` que haremos al `nightscout_api` de cada usuario para obtener el nivel de glucosa, de tal manera que si la conexion al api falla, la aplicacion ejecutara el `except`. Dentro del `except` imprimimos la url del nightscout api del usuario que esta presentando inconvenientes y a su vez ejecutamos `handle_nightscout_failed_pings` la funcion que definimos previamente y que lleva control exacto del numero fallido de pings por usuario y la cual enviara un `sms` al usuario cuando el numero de pings fallidos llegue a su maximo.

En caso que `requests` haya obtenido el nivel glucosa correctamente, se evalua si se encuentre entre `70` y `240` (nuestro rango permitido). Una buena practica es ubicar estos limites en variables de entorno como lo hemos hecho con otras configuraciones de nuestra aplicacion. Si el nivel de glucosa se encuentra en el rango permitido se imprime un mensaje indicando que el nivel de glucosa esta dentro del limite (`print("{0} is inside the range for {1}".format(glucose,active_scout["username"]))`), La misma condicional evalua que en caso contrario se ejecutara la funcion `call_glucose_alert` que hara una llamada al numero de telefono del usuario indicando el nivel de glucosa en la sangre.

A su vez `call_glucose_alert` desencadena el tracking de `Nexmo` el cual estara enviando los `status` de la llamada en cada una de sus fases. Los estados seran enviados a nuestro `event webhook endpoint`  en donde se evalua que de existir un `status unanswered` se procede a ejecutar la funcion `sms_glucose_alert` para el numero favorito y otros numeros relacionados con el usuario que no contesto la llamada.

Para finalizar siempre al final de nuestro `superdi.py` agregamos las lineas siguientes:

```python
#Manage individual schedule Thread Loop
def run_schedule():
    global thread
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except ApplicationKilledException:
            print("Signal Detected: Killing Nightscout-Nexmo App.")
            #clean the schedule
            schedule.clear()
            return "Thread Killed"

if __name__ == "superdi":
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    #run job at second 30 of each minute
    schedule.every().minute.at(':30').do(job, str(uuid.uuid4()))
    #update scouts each our at minute 00
    schedule.every().hour.at(':00').do(refresh_scouts, str(uuid.uuid4()))
    thread = Process(target=run_schedule)
    thread.start()
    print("Nightscout-Nexmo Thread starts")
```

En principio tenemos la funcion `run_schedule`, la cual iniciara un bucle infinito (dentro del thread paralelo al app de Flask) en este loop dentro de la clausula `try` encontramos la linea `schedule.run_pending()`, el mismo es evaluado en cada iteracion para comprobar si existen jobs por ejecutar en el `schedule` y de ser asi los ejecuta. Posterior a esta linea encontrar `time.sleep(1)` esta linea de codigo congela la ejecucion del flujo por 1 segundo antes de evaluar la siguiente iteracion.

En el bloque `except` capturamos las excepciones de tipo `ApplicationKilledException`, la excepcion personalizada que creamos previamente. Si esta excepcion es detectada nuestra funcion procedera a detener el `scheduler` y enviara el mensaje `Signal Detected: Killing Nightscout-Nexmo App.`. La excepcion sera desencadenada cuando el usuario haga `CTRL+C` desde la consola de linux despues de hacer deploy de la aplicacion.

Las siguientes lineas evaluan si el app que se esta ejecutando es `superdi` (el script _superdi.py_). De ser asi con el modulo signal asignamos la funcion `signal_handler` cuando SIGTERM (CTRL+C) y SIGINT (Otro tipo de interrupciones) sean detectadas. Esto lo podemos comprobar en la linea `signal.signal(signal.SIGTERM, signal_handler)`, si el usuario presiona `CTRL+C` SIGTERM sera detectado por signal y la funcion `signal_handler` sera ejecutada desencadenando `ApplicationKilledException` el cual sera detectado por la funcion  `run_schedule` y la misma procedera a detener el `scheduler`.

Las siguientes dos lineas corresponden a la programacion de los `jobs`:

 - `schedule.every().minute.at(':30').do(job, str(uuid.uuid4()))` puede leerse sin dificulta de esta forma. Usando el modulo `schedule` cada `minuto` con `30` segundos ejecutar la funcion `job` y le pasamos el parametro `uuid.uuid4()` que es un `id` de proceso unico generado por el modulo `uuid`.
 
 - `schedule.every().hour.at(':00').do(refresh_scouts, str(uuid.uuid4()))` se leeria de esta forma. Usando el modulo `schedule` cada `hora` a los `00` minutos ejecutar la funcion `refresh_scouts` a la cual le pasamos el id `uuid.uuid4()` generado por el modulo `uuid`.

Una vez que la programacion de los `jobs` ha sido establecida en el `scheduler` definimos el hilo donde correra nuestro `scheduler`. Para ello usaremos `Process` una clase del modulo nativo de python (multiprocessing) importado anteriormente en la linea `from multiprocessing import Process`.

Por un lado la linea `thread = Process(target=run_schedule)` indica que un proceso sera creado y que se ejecutara en un `hilo` independiente. Target representa el nombre de la funcion que define el loop infinito del `scheduler`  que se ejecutara en este hilo.

La linea `thread.start()` indica la ejecucion del proceso anteriormente definido. Hecho esto se creara el hilo en el background el cual puede ser confirmado con el comando `top` en una terminal de linux independiente (deberian detectarse dos procesos de python corriendo)

Para finalizar imprimimos el mensaje `Nightscout-Nexmo Thread starts` para indicar que nuestra aplicacion ha iniciado su ejecucion (Este me mensaje sera detectado por los logs de python, gunicorn u otro server como nginx)

### Deploy de la aplicacion

En este caso para hacer deploy de la apicacion, en nuestra terminal de linux procedemos estando dentro del directorio de nuestra aplicacion procedemos a ejecutar el comando:

gunicorn -b 0.0.0.0:80 superdi:app

Gunicorn respondera que ha iniciado la aplicacion, y el mensaje `Nightscout-Nexmo Thread starts` sera mostrado. Adicionalmente a esto en la funcion `job` la cual se ejecuta cada minuto por `scheduler` tenemos la linea `print("Alerts Job " + id+ "")`. Por ende cada minuto gunicorn mostara en pantalla que el `Alerts Job XXXX-X-X-X-XXXXXXXX` fue ejecutado, asi como otros mensajes que se encuentran en algunas otras funciones de nuestra aplicacion.

De esa forma tambien podremos comprobar que nuestro `Thread` esta vivo y esta corriendo correctamente.

**Tip adicional:** Si queremos hacer deploy en otro server externo al actual necesitaremos la lista de modulos requeridos para que nuestra aplicacion funcione. Y Puede ser tedioso llevar este control de forma manual. Ya que hemos finalizado nuestra aplicacion podemos proceder a ejecutar el comando desde nuestra terminal de linux:

```sh
pip freeze > requirements.txt
```

El comando anterior genera un archivo text llamado requirements en donde tendremos una lista actualizada de todos los modulos requeridos por nuestra aplicacion. En nuestro server externo, solo restaria ejecutar el comando:

```sh
pip install -r requirements.txt
```

Con esta linea se instalarian todos los modulos necesarios para que nuestra aplicacion funcione y ya estariamos listos para deploy.

# Como desplegar nuestra aplicacion en Google Cloud Platform

## Desde Google

En este apartado describiremos el procedimiento para hacer deploy de nuestra aplicacion usando **Google Cloud**, para ello ingresamos a la siguiente url https://console.cloud.google.com y nos autenticamos.

Una vez dentro se nos presentara el dashboard de nuestro proyecto mas reciente, en nuestro el proyecto que creamos para el desarrollo de nuestra aplicacion. De no ser asi, en la seccion superior izquierda deberia aparecer la opcion `Select Project`, desplegamos y seleccionamos nuestro proyecto.

En la parte superior derecha deberia aparecer el icono de la consola de gcloud representado por `>_`. Hacemos clic y nos desplegara la consola, para tener la opcion de editar nuestros archivos en la parte superior derecha de la consola desplegada seleccionar el simbolo de `lapiz`, esto abre una nueva ventana con el editor y nuestra consola cargada justo abajo del editor.

En la consola de google cloud hacemos clone de nuestra aplicacion usando el comando

git clone https://gitlab.com/codeonrocks/nexmo-nsnotifier.git

Siempre desde la consola de `gcloud`, inicializamos el virtual environment para python3, esto es muy practico al usar varias versiones de python o cuando se trabaja en un proyecto, nos permite trabajar de forma aislada del entorno. Por ejemplo para generar los paquetes de nuestra aplicacion con `pip freeze > requirements.txt` si hemos configurado virtual env previamente. Solo seran tomados en cuenta los paquetes que instalamos dentro del virtual env.

```sh
python3 -m venv env
source env/bin/activate
```

Ahora bien abrimos el editor y editamos el archivo `.env`. Configuramos todas las credenciales necesarias en el archivo, desde nuestro directorio local y añadimos todos los privates keys que hagan falta al directorio de nuestro proyecto (Solo es necesario arrastrarlos y google hara upload de los mismos). La variable de entorno `SITE_URL` debera tener la estructura `https://PROJECT_ID.appspot.com` donde `PROJECT_ID` es el id que configuramos para nuestro proyecto

Agregamos el archivo app.yaml con el siguiente contenido:

```yaml
runtime: python
env: flex
entrypoint: gunicorn -b :$PORT superdi:app

runtime_config:
  python_version: 3

manual_scaling:
  instances: 1

```

Este archivo es usando por google cloud cuando se hace deploy. En el configuramos detalles generales de nuestra aplicacion, por ejemplo el lenguaje de programacion, comando necesario para inicializar nuestra app e incluso detalles de infraestructura (Numero de instancias, CPU, memoria ram, tamaño del disco, etc).

En la consola de google cloud nos cambiamos a nuestro directorio y desplegamos la aplicacion

```sh
cd nexmo-nsnotifier
gcloud app deploy
```

`gcloud app deploy` es el encargado de hacer deploy de nuestra app. El mismo crea un contenedor para nuestra aplicacion, instala la version requerida de python, instala todos los paquetes requeridos y ejecuta nuestra App. Este proceso tiende a tardar varios minutos.

Deploy hace recomendacion de los comandos `gcloud app browse` para ver nuestra applicacion en funcionamiento y `gcloud app logs tail -s [INSTANCIA]` para tener acceso a los logs que gennera nuestra aplicacion.

`gcloud app browse` nos notificara que no se encontro ningun browser instalado (ya que este comando se usa normalmente en el CLI). Sin embargo devolvera la url en donde se ha desplegado nuestro App, clic sobre el enlace y podremos ver nuestro app corriendo en google cloud

`gcloud app logs tail -s [INSTANCIA]` Reemplazar `[INSTANCIA]` por el nombre de la instancia que nos asigna google cloud. En el caso de nuestra aplicacion podemos usar el comando para monitorear tambien que nuestro daemon se esta ejecutando cada minuto.

Una forma de monitorear nuestro App es con `APP Engine`. En el menu de navegacion `≡`, Hacemos clic en la seccion `App Engine > Dashboard`. Esto nos carga el _dashboard_ de nuestro proyecto indicando las estadisticas de las instancias que se estan ejecutando. Asi como el `Billing status` y los `Applications errors`.

Hacemos clic en `Services` y podremos acceder a los servicios que tenemos configurados. Cada servicio puede tener multiples versiones. 

Hacemos clic en `Versions`, aca se nos desplegaran cada uno de los contenedores que hemos creado con cada `deploy`. Cada uno de ellos versionado. Desde aca podemos monitorear el status de un container, el numero de instancias que usa, que lenguaje esta usando, etc.

Pero lo mas importante, podremos administrar nuestros contenedores. Es decir,, podemos seleccionar uno de ellos e iniciarlo. O seleccionar uno que se encuentre en status running y detenerlo. O eliminar aquellas versiones viejas y dejar solo los deploys mas recientes.


## Instalar gcloud en nuestro equipo

Descargamos gcloud client sdk. Referencia: https://cloud.google.com/sdk/docs/#deb

En nuestra consola de linux local instalamos las dependencias necesarias  para ejecutar google cloud cli en nuestro equipo.

```sh
apt-get install apt-transport-https ca-certificates gnupg
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
sudo apt-get update && sudo apt-get install google-cloud-sdk
sudo apt-get install google-cloud-sdk-app-engine-python google-cloud-sdk-app-engine-python-extras
```

**Nota:** Como nuestra aplicacion esta hecha en python, instalamos las librerias y modulos de python para google cloud SDK

Una vez instaladas las dependencias inicializamos google cloud en el directorio local de nuestra aplicacion

```sh
gcloud init
```

Se nos indicara que nos logeemos para obtener el codigo de verificacion usando el browser. Una vez obtenido lo introducimos y enter

Una vez dentro se nos indicara que seleccionemos el proyecto en el que queremos trabajar. Google nos presentara el listado de proyectos creados, y en nuestro caso digitamos el numero del proyecto en cuestion y enter

Se nos pedira que elijamos la zona donde queremos correr nuestra instancia. Seleccionamos la zona y enter.

Una vez hecho esto ya podemos usar `gcloud` command normalmente. De esta forma podremos usar los comandos de `gcloud` indicados en el apartado anterior ya que se encuentra directamente conectado a nuestro proyecto.
