const TOKEN_KEY = "weatherAppAccessToken";

let currentUser = null;

const accountButton =
    document.getElementById("account-button");

const accountDropdown =
    document.getElementById("account-dropdown");

const guestAccountActions =
    document.getElementById("guest-account-actions");

const userAccountActions =
    document.getElementById("user-account-actions");

const accountUsername =
    document.getElementById("account-username");

const authDialog =
    document.getElementById("auth-dialog");

const loginPanel =
    document.getElementById("login-panel");

const registerPanel =
    document.getElementById("register-panel");

const profilePanel =
    document.getElementById("profile-panel");


function getAccessToken() {
    return sessionStorage.getItem(TOKEN_KEY);
}


function saveAccessToken(token) {
    sessionStorage.setItem(TOKEN_KEY, token);
}


function clearAccessToken() {
    sessionStorage.removeItem(TOKEN_KEY);
}


function closeAccountDropdown() {
    accountDropdown.hidden = true;
    accountButton.setAttribute(
        "aria-expanded",
        "false"
    );
}


function openAccountDropdown() {
    accountDropdown.hidden = false;
    accountButton.setAttribute(
        "aria-expanded",
        "true"
    );
}


function showGuestAccount() {
    currentUser = null;

    guestAccountActions.hidden = false;
    userAccountActions.hidden = true;

    accountButton.textContent = "Account ▾";
}


function showAuthenticatedAccount(user) {
    currentUser = user;

    guestAccountActions.hidden = true;
    userAccountActions.hidden = false;

    accountUsername.textContent = user.username;
    accountButton.textContent = `${user.username} ▾`;
}


function hideAuthPanels() {
    loginPanel.hidden = true;
    registerPanel.hidden = true;
    profilePanel.hidden = true;
}


function openAuthPanel(panel) {
    hideAuthPanels();

    panel.hidden = false;

    closeAccountDropdown();

    if (!authDialog.open) {
        authDialog.showModal();
    }
}


function closeAuthDialog() {
    authDialog.close();
    hideAuthPanels();
}


function showPreferredCity(city) {
    const cityInput =
        document.getElementById("city-input");

    const searchForm =
        document.getElementById("search-form");

    cityInput.value = city;
    searchForm.requestSubmit();
}


async function fetchCurrentUser() {
    const token = getAccessToken();

    if (!token) {
        showGuestAccount();
        return null;
    }

    const response = await fetch(
        "/api/users/me",
        {
            headers: {
                Authorization: `Bearer ${token}`
            }
        }
    );

    if (!response.ok) {
        clearAccessToken();
        showGuestAccount();
        return null;
    }

    const user = await response.json();

    showAuthenticatedAccount(user);

    return user;
}


async function login(username, password) {
    const formData = new URLSearchParams();

    formData.set("username", username);
    formData.set("password", password);

    const response = await fetch(
        "/api/token",
        {
            method: "POST",
            headers: {
                "Content-Type":
                    "application/x-www-form-urlencoded"
            },
            body: formData
        }
    );

    if (!response.ok) {
        throw new Error(
            "Incorrect username or password."
        );
    }

    const data = await response.json();

    saveAccessToken(data.access_token);

    return fetchCurrentUser();
}


accountButton.addEventListener(
    "click",
    (event) => {
        event.stopPropagation();

        if (accountDropdown.hidden) {
            openAccountDropdown();
        } else {
            closeAccountDropdown();
        }
    }
);


document.addEventListener(
    "click",
    (event) => {
        if (
            !accountDropdown.hidden &&
            !accountDropdown.contains(event.target) &&
            event.target !== accountButton
        ) {
            closeAccountDropdown();
        }
    }
);


document
    .getElementById("open-login-button")
    .addEventListener(
        "click",
        () => openAuthPanel(loginPanel)
    );


document
    .getElementById("open-register-button")
    .addEventListener(
        "click",
        () => openAuthPanel(registerPanel)
    );


document
    .getElementById("open-profile-button")
    .addEventListener(
        "click",
        () => {
            if (!currentUser) {
                return;
            }

            document.getElementById(
                "profile-username"
            ).textContent = currentUser.username;

            document.getElementById(
                "profile-city"
            ).value = currentUser.preferred_city;

            document.getElementById(
                "profile-message"
            ).textContent = "";

            openAuthPanel(profilePanel);
        }
    );


document
    .getElementById("close-auth-dialog")
    .addEventListener(
        "click",
        closeAuthDialog
    );


document
    .getElementById("switch-to-register")
    .addEventListener(
        "click",
        () => openAuthPanel(registerPanel)
    );


document
    .getElementById("switch-to-login")
    .addEventListener(
        "click",
        () => openAuthPanel(loginPanel)
    );


document
    .getElementById("logout-button")
    .addEventListener(
        "click",
        () => {
            clearAccessToken();
            showGuestAccount();
            closeAccountDropdown();
        }
    );


document
    .getElementById("login-form")
    .addEventListener(
        "submit",
        async (event) => {
            event.preventDefault();

            const message =
                document.getElementById(
                    "login-message"
                );

            message.textContent = "Logging in...";

            const username =
                document.getElementById(
                    "login-username"
                ).value.trim();

            const password =
                document.getElementById(
                    "login-password"
                ).value;

            try {
                const user = await login(
                    username,
                    password
                );

                if (!user) {
                    throw new Error(
                        "Unable to load account."
                    );
                }

                message.textContent = "";

                closeAuthDialog();

                showPreferredCity(
                    user.preferred_city
                );

            } catch (error) {
                message.textContent =
                    error.message;
            }
        }
    );


document
    .getElementById("register-form")
    .addEventListener(
        "submit",
        async (event) => {
            event.preventDefault();

            const message =
                document.getElementById(
                    "register-message"
                );

            const username =
                document.getElementById(
                    "register-username"
                ).value.trim();

            const password =
                document.getElementById(
                    "register-password"
                ).value;

            const preferredCity =
                document.getElementById(
                    "register-city"
                ).value.trim();

            message.textContent =
                "Creating account...";

            try {
                const response = await fetch(
                    "/api/register",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type":
                                "application/json"
                        },
                        body: JSON.stringify({
                            username,
                            password,
                            preferred_city:
                                preferredCity
                        })
                    }
                );

                if (!response.ok) {
                    if (response.status === 409) {
                        throw new Error(
                            "Username is already registered."
                        );
                    }

                    throw new Error(
                        "Could not create account."
                    );
                }

                const user = await login(
                    username,
                    password
                );

                if (!user) {
                    throw new Error(
                        "Account created, but login failed."
                    );
                }

                message.textContent = "";

                closeAuthDialog();

                showPreferredCity(
                    user.preferred_city
                );

            } catch (error) {
                message.textContent =
                    error.message;
            }
        }
    );


document
    .getElementById("profile-form")
    .addEventListener(
        "submit",
        async (event) => {
            event.preventDefault();

            const token = getAccessToken();

            if (!token) {
                showGuestAccount();
                closeAuthDialog();
                return;
            }

            const message =
                document.getElementById(
                    "profile-message"
                );

            const preferredCity =
                document.getElementById(
                    "profile-city"
                ).value.trim();

            message.textContent =
                "Saving...";

            try {
                const response = await fetch(
                    "/api/users/me",
                    {
                        method: "PATCH",
                        headers: {
                            Authorization:
                                `Bearer ${token}`,
                            "Content-Type":
                                "application/json"
                        },
                        body: JSON.stringify({
                            preferred_city:
                                preferredCity
                        })
                    }
                );

                if (!response.ok) {
                    throw new Error(
                        "Could not update home city."
                    );
                }

                const user =
                    await response.json();

                showAuthenticatedAccount(user);

                message.textContent = "";

                closeAuthDialog();

                showPreferredCity(
                    user.preferred_city
                );

            } catch (error) {
                message.textContent =
                    error.message;
            }
        }
    );


async function restoreSession() {
    try {
        const user = await fetchCurrentUser();

        if (
            user &&
            user.preferred_city
        ) {
            showPreferredCity(
                user.preferred_city
            );
        }

    } catch (error) {
        console.error(error);

        clearAccessToken();
        showGuestAccount();
    }
}


showGuestAccount();
restoreSession();
