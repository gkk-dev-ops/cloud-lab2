const express = require("express");
const session = require("express-session");
const { Issuer, generators } = require("openid-client");
require("dotenv").config();

const app = express();
const PORT = 3000;
let client;

// Initialize OpenID Client
async function initializeClient() {
  const issuer = await Issuer.discover(process.env.COGNITO_IDP_URL);
  client = new issuer.Client({
    client_id: process.env.CLIENT_IT,
    client_secret: process.env.CLIENT_SECRET,
    redirect_uris: [`http://localhost:${PORT}/auth/callback`],
    response_types: ["code"],
  });
}
initializeClient().catch(console.error);

app.use(
  session({
    secret: process.env.SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
  })
);

const checkAuth = (req, res, next) => {
  if (!req.session.userInfo) {
    req.isAuthenticated = false;
  } else {
    req.isAuthenticated = true;
  }
  next();
};

app.get("/", checkAuth, (req, res) => {
  res.render("home", {
    isAuthenticated: req.isAuthenticated,
    userInfo: req.session.userInfo,
  });
});

app.get("/login", (req, res) => {
  const nonce = generators.nonce();
  const state = generators.state();

  req.session.nonce = nonce;
  req.session.state = state;

  const authUrl = client.authorizationUrl({
    scope: "email openid phone",
    state: state,
    nonce: nonce,
  });

  res.redirect(authUrl);
});

function getPathFromURL(urlString) {
  try {
    const url = new URL(urlString);
    return url.pathname;
  } catch (error) {
    console.error("Invalid URL:", error);
    return null;
  }
}

app.get(
  getPathFromURL(`http://localhost:${PORT}/auth/callback`),
  async (req, res) => {
    try {
      const params = client.callbackParams(req);
      const tokenSet = await client.callback(
        `http://localhost:${PORT}/auth/callback`,
        params,
        {
          nonce: req.session.nonce,
          state: req.session.state,
        }
      );

      const userInfo = await client.userinfo(tokenSet.access_token);
      req.session.userInfo = userInfo;

      res.redirect("/");
    } catch (err) {
      console.error("Callback error:", err);
      res.redirect("/");
    }
  }
);

// Logout route
app.get("/logout", (req, res) => {
  req.session.destroy();
  const logoutUrl = process.env.LOGOUT_URL;
  res.redirect(logoutUrl);
});

app.set("view engine", "ejs");

app.listen(PORT, () => {
  console.log(
    `Example app listening on port ${PORT}, http://localhost:${PORT}`
  );
});
