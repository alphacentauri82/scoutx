# Scout: The Nightscout Notifier

Scout is an application created in `Python`, using `Flask` which includes `jinja2` as a template engine. This allows us to separate the logic of the application from the presentation of the data. On the client side, javascript will be used to develop certain dynamic functionalities required for our App.

# Application features

Scout allows to ping the Nightscout data of a user obtaining the last blood glucose level recorded. If levels are below 70mg/dL(3.9 mmol/L) or above 240mg/dL(13.3 mmol/L), the application will execute a call to the user's mobile phone number and they will hear their current blood glucose level.
If the user does not respond, a text message will be sent to the preferred emergency contact configured by the user and additionally up to 5 extra numbers.

The ping frequency to Nightscout, will be of 1 minute. To be exact, it will be done 30 seconds after each minute using the system clock. This indicates that if a user's glucose level remains out of the standard range during that period of time, the call will be made again. Ideally, you should indicate to the system that if the user has recently been called up for the app to wait 120 seconds to rerun the call workflow.

If the Nightscout service does not respond for 1 hour, an SMS will be sent alerting the user that their service is offline.

The user can sign up/log in using their Google account and configure the following information:

- Nightscout Api Url
- Personal number
- Preferred emergency contact and can add up to 5 additional phone numbers, the user will have the option of not adding any additional emergency contacts.

# Applications Involved

Scout relies on 4 applications for its operation.

- **Nightscout:** Nightscout (CGM in the Cloud) is an open source, DIY project that allows real time access to a CGM (Continuous Glucose Manager) data via personal website, smartwatch viewers, or apps and widgets available for smartextra_contacts.

	Nightscout was developed by parents of children with Type 1 Diabetes and has continued to be developed, 		maintained, and supported by volunteers. When first implemented, Nightscout was a solution specifically for 		remote monitoring of Dexcom G4 CGM data. Today, there are Nightscout solutions available for Dexcom G4, Dexcom 		Share with Android, Dexcom Share/G5 with iOS, Dexcom G6, Abbott Freestyle Libre with MiaoMiao/Blucon and 		Medtronic. Nightscout also provides browser-based visualization for #openAPS users and Loop users. The goal of 		the project is to allow remote monitoring of a T1D’s glucose level using existing monitoring devices.

	In turn, nightscout has an API that allows data to be obtained in json or xml format for use in external 		applications. It is necessary to enable CORS in the user's Nightscout in order to access this information from 		external domains.

	You can get more information in the following links: https://nightscout.info and 	https://github.com/nightscout/cgm-remote-monitor

- **Nexmo:** The Vonage API Platform, provides tools for voice, messaging and phone verification services, allowing developers to embed contextual, programmable communications into mobile apps, websites and business systems, enabling enterprises to easily communicate relevant information to their customers in real time, anywhere in theworld, through text messaging, chat, social media and voice.

	In order to use all these amazing services for our app, we need to create an account, create an application, 		create a virtual number and have sufficient balance to be able to use the service. Check this link for more 		information: https://developer.nexmo.com/

- **Google Auth:** The API that allows us to use the Google authentication service for our web application. More information at https://developers.google.com/identity/protocols/OAuth2

- **Firebase/Firestore:** Firebase provides multiple services such as real-time database, storage, hosting, web services (using functions) and much more. In our case we will use the firebase firestore service to store our data in the cloud.

# Analysis

Given the above features, our application can be divided into two parts:

- An application in Flask that allows the user to log in and configure the application data
- A Python Thread with a scheduler that runs with a given frequency, consulting the nightscout dashboard of each user, sending alerts when necessary. A second scheduler that runs less frequently can be assigned to obtain fresh data.

# Requirements

Before starting with the development of the functionalities described in the previous section, we will review certain features necessary to install python modules or guarantee the execution of our application.

- A linux terminal (OsX is based on Unix so it's similar). This application was developed with ubuntu, debian and has also been tested in WSL.

- Our application will use python 3, to confirm our python version, open our terminal and execute the following command:

  ```
  python --version
  ```

  If the result is `python 3.x.x` we can continue with the next step. Otherwise we must proceed to install python 3.

- Check the pip version (Python module installer). Pip is included by default if we have python 3 installed.

  ```
  pip --version
  ```

  **Note:** The previous command should return the current pip version and tell us which version of python pip works with. It is important to ensure python 3 appears as the version used by pip

- Once we have verified that we have python 3, we proceed to create our application's directory:

  ```
  mkdir Scout
  cd Scout
  ```

- Let's install flask! (We will start with the visual part of our app)

  ```
  pip install Flask
  ```

**Note:** pip will install the necessary dependencies for Flask automatically. For example Jinja (Flask's template engine).

# 1. User Interface Development and Google Auth

In this section we will start configuring Google Auth. We will also proceed to create a simple interface where we will use the Google Auth API, log in view and create a persistent server-side session to keep us logged in until the user decides to log out.

### Google Auth

In order to use Google Auth, we have to obtain a `client ID`, which we will use to call the Google API sign in. Let's head to: https://console.cloud.google.com/home/dashboard, And create a new project.

- Once the project has been created, click on the `navigation menu (≡)` and select `APIs & Services> Credentials`.
- Click on `Create Credentials> OAuth client ID`, we will be presented a form asking what type of application we are developing.
- Select `Web`
- In `Authorized JavaScript sources` and `Authorized redirection URIs` write the domain name to be used for this app. `Eg https:// domain. ext/`, In our case we will assume that `/` will be the endpoint that will consume our authentication service.
- Click on `Create` and our client ID will be generated. It should be listed on `OAuth 2.0 client IDs`. Keep the client ID at hand, since we will use it later.

### Preparations

Let's make a recap of all the necessary requirements before we dive into the source code:

- Use the **clientID**: which we will obtain from a `.env` file (where we will store several environment variables). To obtain these values ​​we will use the `dotenv` module and its function `load_dotenv`.

- Google modules: To re-confirm the identity of the user connected on the backend side.

- Flask modules, which will allow us to handle requests, load templates and create session variables

**`dotenv`,`requests` and the `google modules` are not native to python**, for that reason let's go back to our terminal and proceed to install:

`pip install requests python-dotenv google-auth`

- **Important** : Flask needs a unique key to store our session variables. It's a binary that we have to handle discreetly. Let's generate it:

`python -c 'import os; print (os.urandom (16)) '`

### Diving in the source code

Once we are done with all our preparations, let's open our favorite editor (for example pyCharm or Visual Studio Code). Let's create a new file. You can name it whatever you want, in my case i chose `notifier.py`.

In `notifier.py`:

At the very begining of the file we will import the following modules:

_**This line indicates that the flask module will be importing the mentioned classes and functions
E.g. `render_template` is a function that will load the template that we indicate in our code
While Flask, is the class that will allow us to initialize our application**_

```python
import json, os
from flask import Flask, request, render_template, session
```

In the same way we import some functions that will allow us to read the environment variables. A secure way to handle credentials is to find them available only in the scope of the operating system that runs the application.

```python
from os.path import join, dirname
from dotenv import load_dotenv
```

Let's include the modules for google auth that will allow us to reconfirm the identity of the user from the backend.
This will allow us to create a persistent session if the identity is valid.

```python
from google.oauth2 import id_token
import google.auth.transport.requests
```

And the requests module that allows us to request using the POST or GET methods. It's similar to Axios.

```python
import requests
```

Create a new file and name it `.env` (In the tutorial repo i named it `.example-env` if using my repo, make sure you rename it!) and add the following lines:

```ruby
GOOGLE_CLIENT_ID="YOUR_GOOGLE_AUTH_CLIENT_ID"
SITE_URL="YOUR_SITE_URL"
```

**Note:** Replace`YOUR_GOOGLE_AUTH_CLIENT_ID` with the `clientID` generated by google, and`YOUR_SITE_URL` with the domain name you registered previously `https://domain.ext`. Save the file!

---

Let's go back to `notifier.py` and add the following lines:

```python
app = Flask(__name__)
app.secret_key = [THE KEY YOU PREVIOUSLY GENERATED]
```

We assigned the variable `app` that represents our Flask Application, app will create its own context to make only operations related to the requests made to the flask application

Then we assign the secret_key attribute. ** Look at the letter `b`, this indicates that the value that is waiting for the attribute is a binary **. Paste the value previously generated with `python -c 'import os; print(os.urandom(16))'`

To access the environment variables defined in the `.env` file, we add the following:

```python
envpath = join(dirname(__file__),"./.env")
load_dotenv(envpath)
```

Now, let's define the `get_session` function that evaluates whether there is a specific key within the session variable, returning `None` in case it doesn't exist, otherwise the value of the key is returned. It can be reused in different sections of the program:

```python
def get_session(key):
    value = None
    if key in session:
        value = session[key]
    return value
```

In the following section we begin to define our Flask application. Then the controller for the endpoint `/` that will be our landing page and that will show us the google login button will be created:

```python
@app.route('/',methods=['GET','POST'])
def home():
    if get_session("user") != None:
        return render_template("home.html", user = get_session("user"))
    else:
        return render_template("login.html", client_id=os.getenv("GOOGLE_CLIENT_ID"), site_url=os.getenv("SITE_URL"))
```

The line `@app.route('/,methods=['GET','POST'])` indicates that every request either `GET` or `POST` will be redirected to the `home()` handler where it is evaluated whether the user session exists (i.e. the user is authenticated), then the `home.html` template is loaded (when this template is loaded the user variable is passed to access the authenticated user data from the template), otherwise we load the `login.html` template where the google authentication interface will be displayed (We pass the value of `GOOGLE_CLIENT_ID` and `SITE_URL` previously defined in our`.env`, this second parameter will be used for redirection)

Following the Workflow when the user enters the site the user session variable will not exist, therefore `login.html` will be loaded. The next logical step would be to develop the `home.html` jinja template. But before doing that we need to configure the following details:

- Download `materialize` a framework for front-end development based on material design:
    To access static files (css, js, images, fonts) Flask by default recognises the `static` directory for this purpose. Create this directory from your IDE or from your terminal with `mkdir static`.

- Go to: https://materializecss.com/getting-started.html. Click on download. Unzip the file and move the `css` and`js` directories into the previously created `static` directory. Ideally, keep only the minified versions of the css and js files.

- `Materialize` icons can be downloaded from https://fonts.googleapis.com/icon?family=Material+Icons, once downloaded, create `static/fonts` or in easier words a `fonts` folder inside of `static` and move the font file there.

- Create `style.css` in the `static/css/` directory. Most of the time `materialize` is more than enough to provide the styles to an App but sometimes a style file is necessary to control certain details not contemplated in materialize. Let's add some extra style:

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

.logo {
  font-size: 30px !important;
  padding-top: 5px;
}

div.g-signin2 {
  margin-top: 10px;
}

div.g-signin2 div {
  margin: auto;
}
div#user {
  margin-top: 10px;
  margin-bottom: 10px;
}
div#user.guest {
  text-align: center;
  font-size: 20px;
  font-weight: bold;
}
div#user.logged {
  text-align: right;
}
div#user.logged a {
  margin-left: 10px;
}
body {
  display: flex;
  min-height: 100vh;
  flex-direction: column;
}
main {
  flex: 1 0 auto;
}
div.add_contact {
  height: 20px;
}
div.add-contacts-container {
  padding-bottom: 40px !important;
}
.input-field .sufix {
  right: 0;
}
i.delete {
  cursor: pointer;
}
```

Now, we are ready to create our app's layout. We start by creeating a parent template that defines blocks of content that are used by other child files. Officially this will be our first jinja template 🎉. In order for this file to be recognised by Flask as a template, let's create a `templates` directory inside `static`, and create `layout.html`. Let's add the following code:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <link
      rel="stylesheet"
      href="{{ url_for('static', filename='css/materialize.min.css') }}"
    />
    <link
      rel="stylesheet"
      href="{{ url_for('static', filename='css/style.css') }}"
    />
    {% block head %}{% endblock %}
  </head>
  <body>
    <header class="container-fluid">
      <nav class="teal">
        <div class="container">
          <div class="row">
            <div class="col">
              <a href="#" class="brand-logo"
                ><i class="material-icons logo">record_voice_over</i> Scout =
                Nexmo + Nightscout</a
              >
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
          <!--This is the hashtag used by the nightscout project :) -->
          Scout <a class="brown-text text-lighten-3">#WeAreNotWaiting</a>
        </div>
      </div>
    </footer>
    <script
      language="javascript"
      src="{{ url_for('static', filename='js/materialize.min.js') }}"
    ></script>
    {% block script %}{% endblock %}
  </body>
</html>
```

There are a couple of interesting details to highlight: **The use of blocks** and **the use of the `url_for` function**. In the case of blocks, they are reserved sections for inserting code with jinja from child templates. If we pay attention to the `url_for` function, it generates the url to the javascript and css resources from `static` which is quite a comfortable and elegant way!.

The file structure that we should have up to this point should be:

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
    - notifier.py
```

If everything looks proper, as pointed above, let's create `login.html` in the same `templates` directory. This file will be loaded when the `user` session variable does not exist (that is, the user is not logged in).

```html
{% extends "layout.html" %} {% block head %}
<script src="https://apis.google.com/js/platform.js" async defer></script>
<meta name="google-signin-client_id" content="{{ client_id }}" />
{% endblock %} {% block content %}
<div id="user" class="guest">Welcome guest, You need to authenticate</div>
<div class="row">
  <div class="col s6 offset-s3">
    <div class="card blue-grey darken-1">
      <div class="card-content white-text">
        <span class="card-title">Login To Enter Scout</span>
        <p>
          This application will help you configure alerts to your mobile phone,
          a preferred emergency contact and up to 5 other contacts. If you have
          a nightscout dashboard and you have your api available for external
          queries, You can use this server and when your glucose levels are out
          of range, you will receive a call to alert you and your preferred
          contact(s) of such. If you do not answer the call then a sms is sent
          to your emergency contact(s).
        </p>
        <div class="g-signin2" data-onsuccess="onSignIn"></div>
      </div>
    </div>
  </div>
</div>
<script language="javascript">
  function onSignIn(googleUser) {
    var profile = googleUser.getBasicProfile()
    if (profile.getId() !== null && profile.getId() !== undefined) {
      var xhr = new XMLHttpRequest()
      xhr.open('POST', '{{ site_url|safe }}/login')
      xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded')
      xhr.onload = function() {
        console.log('Signed in as: ' + xhr.responseText)
        //Authenticated so redirect to index
        window.location = '{{ site_url|safe }}/'
      }
      xhr.send(
        'idtoken=' +
          googleUser.getAuthResponse().id_token +
          '&username=' +
          profile.getName() +
          '&email=' +
          profile.getEmail()
      )
    }
  }
</script>
{% endblock %}
```

Notice that the first line for `login.html` is `{% extends "layout.html"%}`. This indicates that `login.html` inherits from `layout.html`, in other words it is a child of `layout.html`. This means that the renderer will load `layout.html` with the code variants that we added in `login.html`. These variants are defined within the blocks allowed in layout. Within `login.html` we use the `head` and `content` blocks.

In the `head` block, we have:

```html
<script src="https://apis.google.com/js/platform.js" async defer></script>
<meta name="google-signin-client_id" content="{{ client_id }}" />
```

The first line indicates that we will be using the Google api for the authentication process and the second is meta data used by google to know our app's `clientID`. Note that within the `content` attribute we have written `{{client_id}}`. When the jinja compiler evaluates this expression, it will print the value of the `client_id` variable that we pass to the template using the `render_template` function.

The next block defined is `content` and in there, we present a message to the user indicating how the application works. Then we have a few lines of Javascript. Basically it is a function connected to the `onSignIn` event, this is used by google to return the user data that is logged in using Google auth.

We obtain the user profile with `googleUser.getBasicProfile()` and we evaluate that if there is an ID, the authentication process was successful and we can proceed to send some data to our server to make an identity reconfirmation with google and in turn create the session.

```javascript
var xhr = new XMLHttpRequest()
xhr.open('POST', '{{ site_url|safe }}/login')
xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded')
xhr.onload = function() {
  console.log('Signed in as: ' + xhr.responseText)
  //Authenticated so redirect to index
  window.location = '{{ site_url|safe }}/'
}
xhr.send(
  'idtoken=' +
    googleUser.getAuthResponse().id_token +
    '&username=' +
    profile.getName() +
    '&email=' +
    profile.getEmail()
)
```

The previous lines connect us to our server using an ajax request. Pay attention to the line `xhr.open ('POST', '{{site_url|safe}}/login');` it indicates the method that the request will use. The url `{{site_url|safe}}` will be replaced by the value of the `site_url` variable that we pass to the template. To be able to do the reconfirmation, our flask application only needs the `id_token`, however we also pass the username and email since we will use them later for other operations.

Once the reconfirmation is done, our server will redirect us to `/`. If the reconfirmation was not successful the user will have to try to log in again. Now, if we look carefully, we haven't defined the `/login` endpoint yet, this endpoint will be responsible for reconfirming.

To create it, let's go back to `notifier.py` and add the following lines:

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

As mentioned above to reconfirm the identity of the user on the server, we only need the `id_token` obtained from Google auth and passed to `/login` using an ajax post request. Then we get `client_id` using `os.getenv("GOOGLE_CLIENT_ID")`.

To make the reconfirmation it is advisable to place our code within a `try` `except` block. For exception handling in case an error ocurrs at the time of making the request.

This verification is done using the `verify_oauth2_token` method and returns an `infoid` that must have a key `iss`, which is a reference to the`issuer`, if the value of the issuer does not match the domain we configured, we assume the verification returns a error and an exception will be generated. If, on the other hand, the response is valid, we proceed to create the persistent session on the server side, assigning `user` to the session object. Within this session we store the `userid`, `username` and `email` of the user.

Once this is done, our server returns the response and the `xhr.onload` event of our ajax request is triggered. Its function is to redirect us to `/`. In `/` our application evaluates if the `user` session exists and if so, it will load the `home.html` template by passing the `session['user']` (Check notifier.py to confirm the information)

Following the logic of our application, the next step is to create `home.html` in the`templates` directory:

```html
{% extends "layout.html" %} {% block content %}
<div id="user" class="logged">
  you are logged in as <b>{{ user.username }}</b> -
  <a id="logout" class="teal-text" href="/logout">Logout</a>
</div>
{% endblock %}
```

Basically this template inherits from layout and in our `content` block we will show the logged user and a`logout` link to close session. The latter is not programmed, to complete the login experience we will define the endpoint `logout` in `notifier.py`. Let's add:

```python
    @app.route('/logout')
    def logout():
        session.pop("user",None)
        return redirect(url_for('home'))
```

Our `logout` endpoint deletes the user session and redirects us to `home`. Back at `home` it will evaluate the session and if it doesn't find any, it will render `login.html`.

**Note:** `url_for` uses the handler name `def home()` for redirection, not the endpoint.(Although it is also valid to use endpoints for redirects.). In the case of `url_for` needing to generate a url in `https`, the line should be: `url_for ('home', _external = True, _scheme = 'https')`. The external parameter indicates generation of an absolute url and scheme the protocol we want to use.

At this point we can test if Google auth works . To test locally, let's run the following command in our terminal:

```sh
    export FLASK_APP=notifier
    flask run
```

We are telling Flask to run `notifier.py`. However, it is advisable to use a more robust server and allows a more efficient handling of our requests thus improving its performance. Therefore, we will use Gunicorn an HTTP WSGI server written in python compatible with multiple frameworks (Flask included).

To install, let's execute the following command in our terminal:

```sh
    pip install gunicorn
```

After installing, from the same terminal window and from our app's root directory, type:

```sh
    gunicorn -b 0.0.0.0:80 notifier:app
```

This command deploys our application to our local server and listens for requests using port 80. With this we should be able to access our app and test if we can log in and log out.

**Note:** To stop our application, hit _ctrl+c_ in the same terminal window where gunicorn is running.

# 2. Storing Nightscout settingswith Firebase/Firestore

In this section we will build a simple interface where our user can add the following data:

- **nightscout_api**: A valid Nightscout url to obtain the glucose level data.(For example https://`domain.ext`/api/v1/entries.json).
- **phone**: The user's mobile number where alerts will go to.
- **emerg_contact**: Preferred emergency contact.(Relative or close friend who can receive alerts)
- **extra_contacts**: An array with 5 additional phone numbers. This is optional.
- **email**: The Google account email address to log in, we will use it as an external key to obtain the logs of a logged-in user.
- **username**: Also obtained from the user's google account, we will use it for data presentation

**Firestore** allows us to handle _collections_ and _documents_ in a similar fashion to **mongodb**. For this application our collection will be called _scouts_; A document from our collection should look like this:

```json
{
  "email": "",
  "username": "",
  "phone": "",
  "emerg_contact": "",
  "nightscout_api": "",
  "extra_contacts": []
}
```

## Adding Firebase Firestore to our project

- Go to https://firebase.google.com/
- Login with your Google or GSuite account
- Click on _Go to Console_
- Click on _Add project_. If our previously created project used for Google auth does not appear on the list, click on _Add project_ . We should see our project name listed on _Enter the name of your project_ . Select it and click on _Continue_, Provide additional information for the next steps and when finished click on **Create project**
- On the Firebase console page, click on `authentication` and in the `sign in method` tab, enable `Google`.
- Click on Database, and select FIRESTORE. Then `Database > Tab Rules`. Modify the existing rule as follows:

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

This is to make sure only logged in users have access to our application.

### Connecting our project with Firebase

Once our project is set up on the Firebase console, we have to generate a Firebase key:

- Login to https://console.firebase.google.com/
- Click on _Project Overview> Project settings_ and select the _Service account_ tab
- Click on the generate new private key option
- Save the json file in our application's root directory. You can rename that file to whatever you want. I used: `super_private_key.json`

The next step is to add the name of our private key file to our `.env`, let's add the following line:

```ruby
FIREBASE_PRIVATE_KEY="./super_private_key.json"
```

With these initial preparations in order, we are ready to connect our application to Firebase/Firestore. In the case of data queries for firestore the ideal scenario in python would be to have a class that we can reuse in our application, to allows us to add, modify or query records (CRUD). This way we keep our code simple, organised and much easier to understand.

Preliminarily to carry out our code, we need to install the python modules that will allow us to perform these operations (back to our terminal!):

```sh
pip install firebase-admin
```

Let's create the `models.py` file and add the following lines:

```python
    import firebase_admin, os
    from firebase_admin import credentials
    from firebase_admin import firestore
    from os.path import join, dirname
    from dotenv import load_dotenv
```

The previous lines indicate which modules we will be using in our `models.py` file. Among these, we can see `firebase_admin` which we will use to connect to our firebase project and perform operations (CRUD) on our _scouts_ data collection. We will use `dotenv` to get the `FIREBASE_PRIVATE_KEY` variable from our `.env`

In the same file we add the following lines:

```python
    envpath = join(dirname(__file__),"./.env")
    load_dotenv(envpath)

    credits = credentials.Certificate(os.getenv("FIREBASE_PRIVATE_KEY"))
    firebase_admin.initialize_app(credits)
```

The first two lines are well known since we have previously used them in `notifier.py` to load our **environment** to extract the value of the `FIREBASE_PRIVATE_KEY` variable. The next two lines connect our application with firebase using the private key we generated earlier. `credits = credentials.Certificate (os.getenv (" FIREBASE_PRIVATE_KEY "))` extracts the private key from the file as well as other additional data and `firebase_admin.initialize_app (credits)` authenticates our application to use firebase and initializes it to perform operations .

Once the connection with firebase is defined, we will proceed to define the case model. Normally when we use technologies such as `SQLAlchemy` to work with`flask` ​​and `sqlite`, the models are classes where we define different attributes that are the fields of the database and use a set of native functions of the model to perform operations on the database.

In our case we will create the `model` class as a "bridge" class that will allow us to use the firestore methods to perform database operations. In other words, _model_ will function as a parent class from which other classes will inherit to return their methods. Then we add the code to the end of the `models.py` file:

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

Within the model class we start defining our constructor. It will accept the `key` parameter representing the name of the collection inside firestore. The builder also initialises the firestore client `self.db= firestore.client()` and the collection `self.db.collection(self.key)`

The `get_by` method receives the name of the field and the value by which we want to filter data from our collection. The line: `docs= list(self.collection.where (field,u'==',u'{0}.format(value)).stream())` runs a query to our firebase collection `self.collection`, and is a reference to this collection defined in the constructor. In our collection we use the `where` method to filter by field and value.

Pay special attention to the character `u`, this will indicate that python will send the field name and the value in `unicode` format. By using the code fragment `u'{0}.format(value)` we are telling python that any value, regardless of type, to be formatted to `unicode`. The `stream` method in turn, returns the flow of documents in a special type of data, so the `list` function is used to convert it into an array that can be traversed from python.

Normally when making a query to firestore to obtain data from a collection, for each record in the collection we will obtain an object with two attributes: the document id and the `to_dict()` method that formats the document to the python dictionary type of data (a format that has a structure similar to json and that makes it easy for us to access each field).

The `get_by` function evaluates whether the document exists. If it exists, it creates a consolidated item with `item= docs[0].to_dict()` to store the document in a variable and with `item['id']= docs[0].id` we add the id to the document to have all the information at our disposition. Another important detail is that **get_by** returns the first document found. We leave this as it is in our case. Once our user logs in with Google, they will only have access to a document which will contain their data (one and only one).

We define the `get_all` method which does not receive any parameters. Its function is to obtain all the documents in a collection, consolidate them by creating a dictionary for each item and fill out an array with each consolidated document. This function returns an array of all the documents in the collection or `none` in case there are no documents.

The `add` method receives the _data_ and _id_ parameters. _id_ is optional but if it exists it allows us to add a new document with a defined id. If the parameter _id_ does not exist the new document will be created with an id automatically generated by firestore. Now the parameter _data_ must be of type `dictionary` and will contain the data that we want to add to our collection.

Finally, we define the `update` method, which receives the parameters _data_ and _id_, both are required. While _data_ contains a _dict_ indicating which fields will be altered with what values, _id_ defines which document in the collection we will be modifying.

Next we will add the scout class. The purpose of this class is to act as an interface that allows us to pass the data of our scout collection more directly without thinking of unnecessary formatting when adding new documents. Let's add the following code to `models.py`:

```python
    class scout:
        def __init__(self, email = '', username = '', nightscout_api = '', phone = '', emerg_contact = '', extra_contacts = []):
            self.email = email
            self.username = username
            self.nightscout_api = nightscout_api
            self.phone = phone
            self.emerg_contact = emerg_contact
            self.extra_contacts = extra_contacts
```

**Note:** We will go into more detail on how this class will be used later.

Finally, let's add the `scouts` class that inherits from the`model` class to reuse its methods and in turn has its own methods to interact with the scout collection. Let's add the code at the end of the `models.py` file:

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

The scouts class inherits from model, in its constructor we call the parent constructor and pass it `scouts` which is nothing more than the key that the `model` constructor expects to reference a collection in firebase.

Then we find the `get_by_email` method, which obtains the first document from the `scouts` collection that matches the email provided. This method will be used to obtain the nightscout data of each user connected using a google account.

The method `getby_personal_phone`, receives a phone parameter (the user's personal telephone) and will return the document associated with that data. This method calls the `get_by` method of the`model` class and it will be very useful to obtain user data when we are running the `nexmo` events webhook.

Finally we have the `add` method, in case _data_ is an instance of the`scout` class, we will convert its attributes to dictionary with `data.__dict__`. The _id_ attribute is optional for this method. Pay attention that this method in turn calls the `add` method of the model class for reuse.

Don't forget to send the file!!⭐️

### Playing with the python console

A very practical (and maybe fun?) way to test what we have done is with the python console. Before the fun begins, first, open the firebase console in your browser and click on the Database option. Make sure to select **Cloud firestore** in the upper left corner next to **Database**.

Let's go to our terminal. From our project folder, execute the `python` command. This will take us to the python console where we can run python code. In the python console we execute the following commands"

- Import our previously created python module

`python >>> import models >>> from models import model, scouts, scout`

- Create an instance of the scouts class called `scout_firebase` and add a document to firebase. Review the firebase console after executing the `add` method. In firestore, a new document will be added with the data provided. Pay special attention to the add method, we pass an instance of the `scout` class with all the corresponding data. Internally the `add` method converts the instance of the class to dictionary.

`python >>> scouts_firebase= scouts() >>> scouts_firebase.add(scout(email='email@gmail.com ',nightscout_api ='someurl', phone ='12345678', emerg_contact='23456789', extra_contacts=['34567890']))`

- Get all the documents from our scouts collection

`python >>> docs = scouts_firebase.get_all() >>> print(docs)`

- Update the document we added (in this case we only update the nightscout_api field), we can check the update in the firebase console. Later we obtain the document using the get_by_email method and print item to confirm that the field value was in effect updated.

`python >>> scouts_firebase.update({u'nightscout_api':'some_testing_url'},docs[0]['id']) >>> item = scouts_firebase.get_by_email('email@gmail.com') >>> print(item)`

To close the python console just type `quit()` and we'll go back to our terminal.

### Create the user data configuration interface

With the defined data models, the next step is to create the interface that will receive the data of the connected user, with google auth, and our application will be in charge of using the model to store this information.

In `notifier.py`, just under the last `import` add the following lines:

```python

.....

import models
from models import model, scouts, scout

.....

```

In this way we add our `models` module to the `notifier.py` script and import the `models`, `scouts`, and `scout` classes from the module to be able to use them. Later, before the lines that define the `get_session` function we add the code that initializes the `scouts` class:

```python

.........


nightscouts = scouts()

def get_session(key):

.........

```

Next, we go on to edit our home function, which controls the endpoint `/`. The function will be modified with the following worlflow in mind: A user authenticates with google auth to our application; If you are authenticating for the first time when `/` is loaded, an empty form will be presented with a `new` flag to indicate to the application that the user will insert a new document to firebase. If, on the contrary, the user who is connecting exists before loading `/` a query will be made to firebase to bring the data related to that email and the information will be shown on the form with the `edit` flag to indicate the application that by submitting the form you will be modifying the document of an existing user.

Currently our home is defined as follows:

```python
@app.route('/',methods=['GET','POST'])
    def home():
        if get_session("user") != None:
            return render_template("home.html", user = get_session("user"))
        else:
            return render_template("login.html", client_id=os.getenv("GOOGLE_CLIENT_ID"), site_url=os.getenv("SITE_URL"))
```

With the additional code, it should then be like this:

```python
@app.route('/',methods=['GET','POST'])
    def home():
        global scouts
        if get_session("user") != None:
            if request.method == "POST":
                extra_contacts = request.form.getlist('extra_contacts[]')
                if request.form.get("cmd") == "new":
                    nightscouts.add(scout(email=get_session("user")["email"], username=get_session("user")["username"], nightscout_api=request.form.get('nightscout_api'), phone=request.form.get('phone'), emerg_contact=request.form.get('emerg_contact'), extra_contacts=extra_contacts))
                else:
                    nightscouts.update({u'nightscout_api':request.form.get('nightscout_api'), u'phone':request.form.get('phone'), u'emerg_contact':request.form.get('emerg_contact'),u'extra_contacts':extra_contacts},request.form.get('id'))
            return render_template("home.html", user = get_session("user"), scout = nightscouts.get_by_email(get_session("user")["email"]))
        else:
            return render_template("login.html", client_id=os.getenv("GOOGLE_CLIENT_ID"), site_url=os.getenv("SITE_URL"))
```

Basically the conditional that assesses if the method accessing to `/` is `POST` is added. If so, it is generally considered that the request has been made from a form.

In this case we would be talking about the user configuration form. If the method used is `POST`, we ask if the flag (in this case `cmd`) is`new`. If so, the `add` method will be executed by adding the user's new document.
**Note:** In the case of `email` and `username` we get them directly from the session since this is data obtained from google auth.

If the flag detected is `edit`, the new values ​​of the form are received and the `update` method of the `scouts` class is executed to update the document of the connected user.
**Note:** `email` and `username` are not modified as they are exclusive data from google.

Regardless of the method used, in `render_template` we pass all the data of the connected user using the variable `scout = nightscouts.get_by_email(get_session("user")["email"])`, to fill the form with the configuration information in if the user exists. The form fields will be empty.

Now, we edit the `home.html` file, this jinja template is loaded only if the user has previously logged in. Currently we only have one line of code within the block content indicating the connected user and the link for logout. Just below this we will add the code that will receive the application data for the user

The block should look like this:

```html
{% block content %}
<div id="user" class="logged">
  you are logged in as <b>{{ user.username }}</b> -
  <a id="logout" class="teal-text" href="/logout">Logout</a>
</div>
<div class="row">
  <div class="col s8 offset-s2">
    <div class="card blue-grey darken-1">
      <div class="card-content white-text">
        <h1 class="card-title">Your Scout Profile</h1>
        <div class="row">
          <form id="scout-form" class="col s12" method="POST" action="/">
            <input
              type="hidden"
              name="cmd"
              value="{{ 'new' if scout == None else 'edit' }}"
            />
            {% if scout!=None %}
            <input type="hidden" name="id" value="{{ scout.id }}" />
            {% endif %}
            <div class="row">
              <div class="col s12 input-field">
                <input
                  placeholder="E.g. https://domain.ext/api/v1/entries.json"
                  value="{{ scout.nightscout_api }}"
                  id="nightscout_api"
                  name="nightscout_api"
                  type="text"
                  class="validate"
                  required
                />
                <label for="nightscout_api" class="white-text"
                  >Enter NightScout Api Entries Url (Entries url finish with
                  <b>entries.json</b>)</label
                >
              </div>
            </div>
            <div class="row">
              <div class="col s12 input-field">
                <i class="material-icons prefix">phone</i>
                <input
                  placeholder="E.g. 50588888888"
                  id="phone"
                  name="phone"
                  value="{{ scout.phone }}"
                  type="tel"
                  class="validate"
                  pattern="[0-9]+"
                  required
                />
                <label for="phone" class="white-text"
                  >Enter your mobile number</label
                >
              </div>
            </div>
            <div class="row">
              <div class="col s12 input-field">
                <i class="material-icons prefix">phone</i>
                <input
                  placeholder="E.g. 50588888888"
                  id="emerg_contact"
                  name="emerg_contact"
                  value="{{ scout.emerg_contact }}"
                  type="tel"
                  class="validate"
                  pattern="[0-9]+"
                  required
                />
                <label for="emerg_contact" class="white-text"
                  >Enter emergency contact</label
                >
              </div>
            </div>
            <div class="row">
              <div class="col s12 add-contacts-container">
                <div class="row">
                  <div class="col s6">
                    <label class="white-text"
                      >Add 5 additional contact numbers:</label
                    >
                  </div>
                  <div class="col s6 add_contact">
                    <div class="right-align">
                      <a
                        onclick="add_contact()"
                        class="btn waves-effect waves-light red"
                        ><i class="material-icons">group_add</i></a
                      >
                    </div>
                    <br />
                  </div>
                </div>
                <div class="divider"></div>
                <div class="contact_numbers" id="contact_numbers"></div>
              </div>
            </div>
            <div class="row">
              <div class="col s12 right-align">
                <button
                  class="waves-effect waves-light btn-small"
                  type="submit"
                >
                  <i class="material-icons left">save</i> Save
                </button>
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

Some observations on the form, if the _scout_ variable is `None`, the flag `cmd` will have the value `new` otherwise the value will be `edit`. The values of the text fields receive `{{scout.phone}}`, so when scout is `None` jinja will print empty. When scout exists the id is received in a hidden type field, this field should not be modified since it is the unique identifier of the document in firebase. The `add_contact()` javascript function is undefined.

Let's add some more code in `home.html`, just after`{% endblock %}`. In this case we will use the `script` block that we define in `layout.html` to define the necessary javascript functions.

```javascript
{% block script %}
 <script language="javascript">
 var contacts_numbers = null;
 var container = null;
 var incremental = 0;
 window.addEventListener('load', function(event){

   container = document.getElementById("contact_numbers");
   contact_numbers = container.getElementsByClassName("contact_number");

   var extra_contacts = validate({{ scout.extra_contacts|safe }});
   //var extra_contacts = {{ scout.extra_contacts|safe if scout else "Array()" }};
   for(var p=0;p<extra_contacts.length;p++){
    add_contact(extra_contacts[0]);
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
   div.innerHTML += '<div class="col s12 input-field"><i class="material-icons prefix">contact_phone</i><input placeholder="E.g. 50588888888" name="extra_contacts[]" value="'+value+'" type="tel" class="validate" pattern="[0-9]+"><i class="material-icons prefix sufix delete" onclick="delete_contact(\'id_'+incremental+'\')">delete</i></div>';
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

In the `script` block we define three functions and the event listener of `onload` page. The `validate` function that evaluates whether the value of `{{scout.extra_contacts|safe}}` passed by jinja is empty. If that's the case, then `validate` returns an empty `Array()`, otherwise jinja returns the `extra_contacts` array.

Later we define the function `add_contact()`, this function will dynamically add a text field where the user can type an additional telephone number of the 5 allowed. Each input will have an icon to be clicked on to eliminate the recod. This same function evaluates whether the number of allowed contacts has been reached. In that case `M.toast` of materialize is used to display an alert to the user indicating that they cannot add more than 5 contact numbers. This function is triggered when loading `/` and when clicking on the button to add telephone numbers.

The `delete_contact()` function removes the record created by `add_contact()`. The function is triggered from the `onclick` event of the delete icon added by `add_contact` for each input.

Once this is done, we analyse the `eventListener` created for `onload`. When loading `/`, the validate function is used to evaluate if the value `{{scout.extra_contacts|safe}}` is empty (when a new record is being added or when the user has not added any phone number). If that's the case, validate returns an empty javascript array since jinja doesn't print anything.
In case `extra_contacts` has data `{{scout.extra_contacts|safe}}` will return a manageable array from javascript. In addition to this, then we find the comment `var extra_contacts = {{scout.extra_contacts|safe if scout else "Array()"}};` this method tells us that jinja will return an array in case scout exists, otherwise, print an empty array. This method is also valid for manipulating data passed from jinja to javascript.

If when loading the page, `extra_contacts` contains information, the function `add_contact` is executed for each position of the `extra_contacts` array, passing the value of the phone number to locate it in the value attribute of the input.

With these last details we have concluded configuring google auth login and firebase/firestore for storage and reading data.

At this point we should be able to log in with Google, add our nightscout configuration from the form, save our data in firestore, modify our configuration and properly log out.

# 3. Setting up/configuring the app in Nexmo and creatin a cheduler in Python for Nightscout alerts

In the previous section we finishedthe part of our application where the user can add, edit and check their settings from a UI created in flask with jinja using google auth for authentication and firebase/firestore for data storage.

From now on we will focus on the creation of a thread that runs independently to execute a function with a given frequency to make a `call` to their own contact number, to alert them when their blood glucose level is outside the ranges previously set for high/low. In case the user does not respond, the application should proceed to send an `sms` to the emergency contact registered by the user and up to five additional numbers to alert them in case the user does not respond. If after a reasonable time the glucose level remains outside the allowed range, the application repeats the process.

Another case contemplated is that if the `nightscout_url` does not respond after 1h, the application must send an `sms` indicating the user that their Nightscout service hasn't received any data.

## Create and configure a Nexmo account

- Go to: https://dashboard.nexmo.com/sign-up

- Add your company information and click Sign up. Nexmo sends a PIN to your phone as a text message or automated phone call. The timeout for each verification attempt is 5 minutes. **Note:** you can associate a phone number with one account only. If your phone number is already associated with a Nexmo account you should remove that phone number from the existing account.

- In Phone number verification, enter the PIN sent to you by Nexmo and click Verify. You are logged into Dashboard and shown how to start developing with Nexmo. This page is displayed each time you login until you have made your first successful call with Nexmo API.

- When you create your Nexmo account you are given €2 free test credit and your account is set in DEMO mode. You can use our products to send messages to up to 10 destination numbers, `[Nexmo DEMO]` is added to all the SMS you send. To move out of the Demo mode add credit to your account.

- For very few countries we cannot create a Nexmo account automatically. This is because of payment restrictions or legal trading restrictions for a US registered company.

### Retrieve your account information

To retrieve your Nexmo account information:

- Sign in to Dashboard.

- On the top-right of Dashboard, click the arrow next to `<username>`, then click Settings. In API settings, you see your API key and API secret. You need these values for all API calls.

**Note**: An additional and very important detail is that this account is **free** and has a basic balance for testing with `Voice API` and`SMS`. However, this balance will be limited to making outbound calls and sms, in order to control the flow of `inbound` calls (incoming calls made by the client) it is necessary to upgrade the account to buy a `virtual number` which we will track using `event webhooks`. It is recommended (but not strictly necessary for this application) to upgrade your account have a virtual number assigned to have unlimited access to all Nexmo features!

Please copy the **_apikey_** and **_apisecret_** values to`.env` as follows:

```ruby
  NEXMO_API_KEY="YOUR API KEY HERE"
  NEXMO_API_SECRET="YOUR API SECRET HERE"
```

### Create a Nexmo Application

In order to achieve our goal we need to make calls and send messages. We must create an application that uses the `VOICE API` (https://developer.nexmo.com/voice/voice-api/overview) and `MESSAGES API` (https://developer.nexmo.com/messages/ overview).

To send messages using the `MESSAGES API`, we need our `api_key` and `api_secret`. To use the `VOICE API` we need the `APPLICATION_ID` and `PRIVATE_KEY` to be able to generate JWT (JSON Web Token) credentials that verify our identity and guarantee the transparent exchange of messages between our app and our Nexmo application that will support `Voice` for making calls.

In other words, we have to create a Nexmo application with `VOICE API` and`MESSAGES API` enabled.

- Go to your Nexmo dashboard. On the left sidebar click on the `Your applications`.

- Click on `Create a New Application`.

- Enter the application details as requested.

- Enable `Voice`. When selecting `Voice`, the application will request webhooks urls: `event url`, `answer url` and `fallback answer url`.

  - **Event url**: The url of our server, to which Nexmo will send the tracking of all the events that occur in our voice API. For example, when making a call, Nexmo will send each of the status of the call: ringing, answered, unanswered and complete. For the application we are building this is essential since we need to know the status of the call made to a user since one of our conditions is that if the user does not answer (`unanswered`),`sms` are sent to other number(s) registered by the user . In this field a similar value will be assigned to `https://domain.ext/events` where `domain.ext` is the domain name we chose for our app.

  - **Answer url**: Assigned for `inbound` calls from Nexmo. For example, when a client makes a call to a `Nexmo virtual number`, Nexmo automatically connects the call to the answer url (which will also be defined on our server) and it returns an NCCO (Nexmo call control object) that defines the flow of the call. (More information about NCCO - https://developer.nexmo.com/voice/voice-api/ncco-reference) In our particular case it is not so necessary to define a answer url since we will be passing our NCCO directly in the `create_call` function of `VOICE_API`. However, to define a value it should be similar to `https://domain.ext/answer`.

  - **Fallback answer url**: If for some reason the `inbound` call cannot be made, the call will be redirected to the `Fallback answer url`, which is normally a NCCO responding to the user that there has been a problem and that the call could not be established. In our case it does not apply, because we are using `outbound` calls. So for now we can leave the field empty.

- Enable `Messages`: In case of messages, two urls are requested:

  - **Inbound url**: It is possible to connect our messages application with other applications. For example the `Facebook Messenger` of a facebook page. If a user sends a message to messenger, of a Facebook page connected to the Nexmo App, the message is received through the `inbound` url where we can manipulate and even store it in a database. The data indicates what type of channel was used, the user who sent it and the message sent.

  - **Status url**: The purpose of this field is quite similar to the `Event url`, only that in this case the server will track the status of the messages. If the message was delivered and even if it was read by the user.

  - Both urls will have nomenclatures very similar to the previous ones, for example: `https://domain.ext/inbound` and `https://domain.ext/status`. However, for this application it is not necessary to configure any of those since we will be sending outbound `sms` using the messages api.

**Note:**This was a detailed explanation of each field and what they would be used for but in our particular case, the only `Webhook` that defined is the `event url` of the `VOICE API`.

- Finally click on `Generate new application`.

So, to recap, we created and configured our Nexmo application. If our account is upgraded, there will be a link to buy a Nexmo virtual number (`Buy new numbers`). It is possible to link a Nexmo virtual number to our application so that the outbound calls do not appear as unknown numbers. It is very convenient since the contact can be stored as "Scout" or "Nightscout Alerts". If applicable/desired you can purchase a virtual number and then link it to this application.

That's all we needed to do in order to create our Nexmo application. Now we proceed to obtain the `APPLICATION_ID` and `PRIVATE_KEY`. We can retrieve those values from our dashboard, going to "Application details".

In order to display your `PRIVATE_KEY`, click on `Edit` and then click on `Generate public and private key`. This will trigger a file download containing our private key. Move the generated file to the root application folder. Rename it `nexmo_private.key`.

### Sending alerts with Nexmo

Let's edit our `.env` file and add the following:

```ruby
NEXMO_APPLICATION_ID="NEXMO_APPLICATION_ID"
NEXMO_PRIVATE_KEY="./nexmo_private.key"
NEXMO_NUMBER="NEXMO_VIRTUAL_NUMBER"
```

Remember to replace these values with your information. If you don't have a virtual number, you can use `Nexmo` as a value.

Our application will ping a Nighscout dashboard every minute and get the user's blood glucose level. In case this level is not in the allowed range, the application will call the user alerting them of such. However, without an important modification, if values remain out of range after considerable period of time even after the user has taken the call, it will be made every minute, for that reason we will establish an additional variable called `WAIT_AFTER_CALL` to prevent this from happening. Another variable that we will define is `NEXMO_FAILED_PING_SMS` to control the number of failed pings for the user's Nightscout, the default number will be `60` (equivalent to 1 hr) considering that each ping will be made every minute. In case the number of failed pings reaches this value, an `sms` will be sent to the user to alert them their service has been offline for an hour.

Let's add the following to the end of our `.env` file:

```ruby
WAIT_AFTER_CALL="120"
NEXMO_FAILED_PING_SMS="60"
```

Making an inventory of the modules we need to develop this part of the application, we need to create a Thread to execute our job. Python has `Thread` and `Multiprocessing`, both native modules. We will make some requests to obtain information from the Nightscout api and to use the messages api to send`sms`, we can use the `requests` module (previously installed).
If possible a scheduler that allows us to execute a function periodically and that runs in the `Thread` that we create with `Multiprocessing`. The `schedule` module fits perfectly, and logically we will use the `Nexmo` module to use `VOICE API` when connecting to our Nexmo Application.

Go to terminal and run the following command:

```sh
pip install nexmo schedule
```

Now, go to `notifier.py`, and under the last import add the following:

```python

import nexmo, schedule, time, signal, uuid

from multiprocessing import Process

```

Additionally we will use the native `signal` module to detect **SIGTERM** (CRTL + C) used to terminate an application from the console, `uuid` to generate an unique identifier for our process running in the `Thread`.

In the same file (`notifier.py`), before the definition of the `get_session` function, add the following lines:

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

With `client = nexmo.Client` we initialize the Nexmo client, as we will be using `VOICE API` the values ​​that we will be passing are our `NEXMO_APPLICATION_ID` and the `NEXMO_PRIVATE_KEY`. These values are stored in our environment variable file (`.env`), so we simply get them ​​using `os.getenv` as we have been doing so far.

The line below `active_scouts = nightscouts.get_all()` gets the complete list of registered users so far. This list will be updated every hour to detect changes made by the client from the `user interface` that we previously created.

In `notifier.py`, after the endpoint definition `/ ogout`. We will add the functions responsible for notifications to users. We will start with the function that notifies the user indicating that the Nightscout service is not responding, for this we will use the `MESSAGES API` since we will be sending an `sms`:

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

Before defining the `handle_nightscout_failed_pings` function,`nightscout_failed_pings = {}` is a variable that will control the number of failed pings per user. In this case, the object's key (index) will be the user's phone number and the failed ping count.

The `handle_nightscout_failed_pings` function receives as parameters `to`, `api_url` and `username`. The parameter `to` is the telephone number of the user, `api_url` is the Nightscout api url that is presenting the connection problem and `username` is the name of the user to which the `sms` will be sent to.

Initially, the function evaluates whether the `to` key is present in the `nightscout_failed_pings` object, otherwise the key in the object is initialized with the value of _1_. If it exists, the value increases by _1_.

After the conditional `if nightscout_failed_pings[to] == int(os.getenv("NEXMO_FAILED_PING_SMS")):` is evaluated, indicating if the number of failed pings has reached the maximum as per our settings, an `sms` is sent notifying the user.

The `Messages API` is on `BETA`. For that reason the functions for Python have not yet been incorporated into the `Nexmo` library. To send the message we proceed to use requests and we will use the `url` of `messages api` to make our request.

The method to use when making the request will be `POST`, the first parameter `https://api.nexmo.com/v0.1/messages`, corresponds to the url of the messages api, as the second parameter authentication, in this case we are Using `MESSAGES API` to send `sms`, just authenticate us by passing the `NEXMO_API_KEY` and the `NEXMO_API_SECRET` obtained from our environment variables. This is reflected in `auth = HTTPBasicAuth(os.getenv("NEXMO_API_KEY"),os.getenv("NEXMO_API_SECRET"))`. In the header we define that the data will be sent in `JSON` format.

The `JSON` is structured in three sections: `from` where the channel we will use to send the message (whatsapp, messenger, sms) is defined, in our case it is `sms`, then the `number` that represents the telephone number from where we send the `sms` (here we assign the value of the environment variable `NEXMO_NUMBER`). In the `to` section we also define `sms` in the `type` and in `number` we assign the value of the `to` parameter that our function receives, which is the destination number to where the `sms` will be sent. The `message` section is where the type of content we will send (image, video, text) is indicated. The notification `type` is `text` and `text` (message to be sent) receives the value of `"Dear {0} the Nexmo api url: {1} is not responding, please check the service".format(username, api_url)` where `{0}` is replaced by the value of `username` and`{1}`by the value of `api_url`.

Once the notification is sent, the failed pings count is reset to `0`. If in the response returned by Nexmo there is a `message_uuid` key the function returns `True` indicating that the message was sent. Every message or call made by/to `Nexmo` has its own `uuid`. In case `Nexmo` has not generated the `message_uuid`, the function assumes that the message was not sent and `False` is returned.

At the end of our file let's add the following function, which will also send the user's glucose level to a number chosen by the user in the _UI_:

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

The `sms_glucose_alert` function is quite similar to `handle_nightscout_failed_pings` in the sense that exactly the same procedure is used for sending _sms_. The difference is that it will be indicating the **glucose level** instead of the **api url**. In this function an additional comment has been added clarifying that sending `sms` will be done using the `MESSAGES API` not the `SMS API`.

Then we add the function `call_glucose_alert`:

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

If we look carefully we have added the variable `last_call`, which plays a role similar to `nightscout_failed_pings`. `last_call` is an object and its index will be the user's phone number and the value of the index will be the current time. At the beginning of the function, it is evaluated if the `to` key exists in `last_call`, if there is one, we evaluate if the period between the current time and the time in which the last call of a particular user was made has not reached the value of our `WAIT_AFTER_CALL` environment variable. If this conditional returns `True` a message is printed indicating that an additional time is expected since the number was recently called and `False` is returned preventing the call from being made again "too soon".

If `to` does not exist in `last_call`, we initialize it with the value `time.time()` which reflects the current time in seconds, which in turn is a timestamp that we will be using to make calculations. For example: The time elapsed in _seconds_ since the last call is calculated in `int(time.time() - last_call[to])` and we compare it with the value of `WAIT_AFTER_CALL` which we measure in _seconds_.

To make the `call` using the `VOICE API`, we will use the `create_call` function of the Nexmo module. Previously we have initialized the `Nexmo` client using the `application_id` and the `private_key` indicating that we have all the preparations in place to use the `VOICE API`.

The `create_call` method of `client` receives a single Python dictionary as an object, its nomenclature is very similar to that of `JSON` objects, facilitating its manipulation since `JSON` is very well known and simple to implement.

Like `MESSAGES API`, the `create_call` function has the `to` and `from` sections. The only variant of these sections is the `type` which in this case will be `phone` indicating that a call will be made. In `from` the value of `number` will be our `NEXMO_NUMBER` and in `to` we will assign the parameter `to` that our function receives.

Subsequently we have the section `NCCO`. An `NCCO` is a `JSON` that indicates Nexmo the flow of actions that will be performed on the call. An `NCCO` can be passed in two ways to `create_call`: through the `answer_url` that would be an endpoint on our server, which function is to return the `NCCO` in `JSON` format. This provides a great advantage when creating applications with extended workflows. Since we can generate custom `NCCO`'s from the server, depending on multiple factors, in the case of our application the action will be to reproduce a message to the user indicating glucose level values, for that reason we will use the second method that is to pass the `NCCO` as an object directly to our `NCCO` section of `create_call`.

The `NCCO` section has the key `action` and its value is `talk`. This action tells Nexmo that when making the call, a message will be `speech` (read to the user over the call). It is worth mentioning that `Nexmo` supports the reproduction of `speech` in different languages!!. Subsequently we have the key `text` where the text that we want reproduced in the `call` is defined. For more information on `NCCO` and actions visit the following link: https://developer.nexmo.com/voice/voice-api/ncco-reference

Then define the `eventUrl` which is a Nexmo `webhook` to send information to our server. `EventUrl` is an endpoint of our server that will be receiving a request from Nexmo in `JSON` format with information on the different states of the call. This is very convenient for us since we are interested in capturing the `unanswered` status, to send our `sms` to their emergency contact and additional numbers if applicable. For more information on status that will arrive at the `eventUrl` visit https://developer.nexmo.com/voice/voice-api/guides/call-flow

Like `MESSAGES API`, in the `VOICE API` Nexmo generates a unique `uuid` for each call made. If our answer does not have a `uuid` generated the function returns `False`, assuming that the call cannot be made and otherwise `True` if the call was made and the `uuid` was generated consequently.

**Important note**: The `call_glucose_alert` function is the initial trigger of the Nexmo workflow.

Let's add our `event` webhook endpoint, at the end of our `notifier.py`:

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
                sms_glucose_alert(uscout["emerg_contact"], uscout["username"],glucose)
                #print('sms simulation to: {0} {1} {2}'.format(uscout["emerg_contact"], uscout["username"], glucose))
                for phone in uscout["extra_contacts"]:
                    #print('sms simulation to: {0} {1} {2}'.format(phone, uscout["username"], glucose))
                    sms_glucose_alert(phone, uscout["username"],glucose)
    return "Event Received"
```

In case the user's glucose level is not within the allowed range, the `call_glucose_alert` function that makes a call using `VOICE API` will be executed. At the time of making the call Nexmo sends information to the event webhook to inform about the `started` state, when the phone starts to ring Nexmo sends information to the event webhook indicating the status `ringing` and so on with the rest of the call statuses.

To obtain the information that Nexmo sends to our `event webhook` we will use `req = request.get_json()`, we can uncomment `print(req)` that follows to analyse the structure of the `JSON` using `gunicorn`.

Because we are interested in evaluating the status of the call, we make a conditional querying if `status` exists for `req`. There is a second conditional that assesses whether the value of the status is unanswered. If so, we capture the phone number where the call was not answered using `phone = req["to"]` and use our model to obtain the record related to this phone `uscout =nightscouts.getby_personal_phone(phone)`.

If the record exists, we will recover the last glucose levels for the user, with `requests` and the `get` method, as follows `entries = requests.get(uscout["nightscout_api"]).Json()` and from there we get the last glucose level registered for the user `glucose = entries[0]['sgv']` (Nightscout API orders the entries in descending order, indicating that the last glucose level will be the first). With the glucose level obtained we use the `sms_glucose_alert` function to send an `sms` indicating the user's glucose level to their emergency contact and any additional numbers registered.

With this we have finished the functions section for sending notifications!! 🍾

## Using Scheduler to sendi automatic notifications

In this section we will add the code responsible for creating a parallel thread to our `Flask` application, which will be executing the `scheduler` which in turn will evaluate the glucose levels of the user of our the application and will execute the function `call_glucose_alert` if the glucose level is not in the allowed range. In addition to this, the scheduler is responsible for executing the `handle_nightscout_failed_pings` function that will evaluate the number of failed connection attempts to the user nightscout and will send the notification when it has reached the maximum number of allowed attempts.

Let's add the following lines to the end of the `notifier.py`:

```python
thread = None

class ApplicationKilledException(Exception):
    pass

#Signal handler
def signal_handler(signum, frame):
    raise ApplicationKilledException("Killing signal detected")

```

In the previous lines we defined some functions and variables. `thread` is the variable that we will assign to our parallel thread,`ApplicationKilledException` is a custom class that inherits from `Exception`, created by us with the only task of triggering when the `signal_handler` function is executed. Then, we defined the `signal_handler` function that triggers our custom `Exception`. The idea of `signal_handler` is to give us a more control when the process is stopped by human intervention (by doing CTRL + C) or with the kill command.

By having greater control we can execute certain additional operations to stop our scheduler correctly.

```python
def refresh_scouts(id):
    global active_scouts
    active_scouts = nightscouts.get_all()
    print("Refresh Scouts Job " + id+ "")
```

`refresh_scouts` is a function that updates the value of the variable `active_scouts` during the life cycle of our application. It will be executed by a second scheduler within our `Thread` every hour. The purpose of this function is to keep recent information of our firebase scout collection. That way if a user has made changes through the UI, these changes would be available when `refresh_scouts` is executed.

Another interesting detail is that it receives the parameter `id`, this is because the scheduler, when executing a job will have to identify it with a unique `id`, in order to be able to edit the configuration of execution of a job in real time or to kill a particular job.

Let's continue to add the following lines of code at the end of our `notifier.py`:

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

The `job` function will be our main job, the function will be executed every minute by scheduler. Starts by reading the `active_scouts` variable, which will be updated every hour using the `refresh_scouts` function. Then proceeds to evaluate each of the users using `for active_scout in active_scouts:`.

Within `try` we place the `request` that we will make to the `nightscout_api` to obtain the glucose level, so that if the connection to the api fails, the application will execute `except`. Within the `except` we print the url of the nightscout api of the user who is presenting inconveniences and in turn we execute `handle_nightscout_failed_pings`, a function that we previously defined and that takes exact control of the failed number of pings per user and which will send an `sms` to the user when the number of failed pings reaches its maximum.

If `requests` have obtained the glucose level correctly, it is evaluated if it is between`70` and `240` (our allowed range). A good practice is to locate these limits in environment variables as we have done with other configurations of our application. If the glucose level is within the permitted range, a message is printed indicating that the glucose level is within the limit (`print (" {0} is inside the range for {1} ". Format (glucose, active_scout [" username "]))`), The same conditional evaluates that otherwise the `call_glucose_alert` function will be executed that will make a call to the user's telephone number indicating the blood glucose level.

In turn `call_glucose_alert` triggers the tracking of `Nexmo` which will be sending the `status` of the call on each of its phases. The states will be sent to our `event webhook endpoint` where it is evaluated that if there is an `unanswered status` the function `sms_glucose_alert` is executed for the emergency contact(s) as describe previously.

In our `notifier.py` let's add the following lines:

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

if __name__ == "notifier":
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

Observe the `run_schedule` function, which will initiate an infinite loop (within the parallel thread to the Flask app). In this loop, inside the `try` clause, we find `schedule.run_pending()`, it checks if there are jobs to be executed in the `schedule` and if so, execute them on each iteration. After this, notice `time.sleep(1)`. This freezes the flow execution for 1 second before evaluating the next iteration.

In the `except` block we capture the exceptions of type `ApplicationKilledException`, the custom exception we created previously. If this exception is detected, our function will proceed to stop the scheduler and send the message Signal Detected: Killing Nightscout-Nexmo App. The exception will be triggered when the user hits `CTRL+C` from terminal after deploying the application.

The following lines evaluate whether the app that is running is `notifier` (the _notifier.py_ script). If so, with the signal module we assign the `signal_handler` function when `SIGTERM` `(CTRL+C)` and `SIGINT` (Other types of interruptions) are detected. We check with `signal.signal(signal.SIGTERM,signal_handler)`, if the user presses `CTRL+C`, `SIGTERM` will be detected by signal and the `signal_handler` function will be executed by triggering `ApplicationKilledException` which will be detected by `run_schedule` and it will proceed to stop the `scheduler`.

The following two lines correspond to the programming of the `jobs`:

- `schedule.every().minute.at(':30').do(job, str(uuid.uuid4()))` Is easy to reead and understand. Using the `schedule` module every `minute` and `30` seconds, executes the `job` function and passes the parameter `uuid.uuid4()` which is a unique process `id` generated by the `uuid` module.

- `schedule.every().hour.at(':00').do(refresh_scouts, str(uuid.uuid4()))`: using the `schedule` module every `hour` at `00` minutes execute the `refresh_scouts` function to which we pass the id `uuid.uuid4()` generated by the `uuid` module.

Once the programming of the `jobs` has been established in the `scheduler` we define the thread where our `scheduler` will run. For this we will use `Process`, a class of the multiprocessing native module previously imported in `from multiprocessing import Process`.

`thread = Process(target = run_schedule)` indicates that a process will be created and that it will be executed in a separate `thread`. `Target` represents the name of the function that defines the infinite loop of the scheduler that will be executed in this thread.

The `thread.start()` line indicates the execution of the previously defined process. Once this is done, the thread will be created in the background which can be confirmed with the `top` command in your terminal (two running python processes should be detected).

Finally, we print the message `Nightscout-Nexmo Thread starts` to indicate that our application has started its execution (This message will be detected by any Python, gunicorn or other server logs like nginx).

### Running our application locally

To run our app locally, head back to terminal, and from our app root directory run the following command:

```sh
gunicorn -b 0.0.0.0:80 notifier: app
```

Gunicorn will respond that the application has started, and the message `Nightscout-Nexmo Thread starts` will be displayed In addition to this, in the `job` function which is executed every minute by `scheduler` we observe`print("Alerts Job"+id+" ")`. Gunicorn will show on screen that the `Alerts Job XXXX-X-X-X-XXXXXXXX` was executed, as well as other messages found in some other functions of our application.

That way we can also check that our `Thread` is alive and running correctly.

**Additional tip:** If we want to deploy on another server external to the current one, we will need the list of modules required for our application to work. And it can be tedious to carry out this control manually. Since we have finished our application we can proceed to execute the following command from our terminal:

```sh
pip freeze > requirements.txt
```

This command generates a text file called `requirements` where we will have an updated list of all the app's required modules, so when we clone our repository, to our external server we only have to run:

```sh
pip install -r requirements.txt
```

After running the above command, we are ready to deploy our application!!.

# 4. Deploying our application on Google Cloud Platform

In this section we will describe the procedure to deploy our application using **Google Cloud Platform**. Proceed to https://console.cloud.google.com and authenticate.

We have previously created a project but in case you have more than one active project, click on `Select Project` and select the project associated with our app.

Click on the gcloud console icon (`>_`).This will display the console. In order to edit our files, select the `pencil` symbol, this opens a new window with an editor and our console loaded just below the editor.

In the Google Cloud console, let's clone our application:

```sh
git clone https://github.com/alphacentauri82/nexmo-scout.git
```

Init the virtual environment for Python3. This is very practical when using several versions of Python or when working on a project, it allows us to work in isolation from the environment. For example to generate the packages of our application with `pip freeze> requirements.txt` if we have previously configured virtual env. Only the packages that we install inside the virtual env will be taken into account.

```sh
python3 -m venv env
source env/bin/activate
```

Let's open the editor and edit the `.env` file. We will configure all the necessary credentials, from our local directory and add all the private keys that are needed to the directory of our project (It is only necessary to drag and drop them and google will upload them). The environment variable `SITE_URL` should have the structure`https://PROJECT_ID.appspot.com` where `PROJECT_ID` is the id that we set for our project

Let's add add the `app.yaml` file with the following content:

```yaml
runtime: python
env: flex
entrypoint: gunicorn -b :$PORT notifier:app

runtime_config:
  python_version: 3

manual_scaling:
  instances: 1
```

This file is used by google cloud to deploy. It contains general details of our application, for example the programming language, the necessary command to initialize our app and even infrastructure details (Number of instances, CPU, ram memory, disk size, etc).

Let's head back to the google cloud console, switch to our app directory and deploy the application:

```sh
cd nexmo-scout
gcloud app deploy
```

- `gcloud app deploy` deploys our app. It creates a container for our application, installs the required version of python, installs all required packages and runs our App. This process tends to take several minutes.

- With `gcloud app browse` we can see our application running and with `gcloud app logs tail -s [INSTANCE]` we can access the our application logs.

- `gcloud app browse` will notify us that no installed browser was found (since this command is normally used in the CLI). However, it will return the url of our Application, click on the link see it live!

- `gcloud app logs tail -s [INSTANCE]`: Replace `[INSTANCE]` with the name of assigned instance by google cloud. In our particular case we can use this command to monitor that our daemon is running every minute.

- `App Engine` is also a good way to monitor our app. Click on the hamburguer menu (`≡`). Then go to `App Engine> Dashboard`. It will load our project _dashboard_ and display stats of all the running instances. As well as the billing and error information.

- Click on `Services` to access the services we have configured. Each service can have multiple versions.

- Click on `Versions`, here we can see each container created with each `deploy`. Each of them versioned. From here we can monitor the status of a container, the number of instances it uses, what language it is using, etc. Most important, we can manage our containers. We can start and stop them or remove old versions and keep the most recent deploys.

Hooray! we built a robust Flask app and deployed it!! 🎉
