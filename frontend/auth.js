const TOKEN_KEY = "weatherAppAccessToken";

let currentUser = null;
let passwordResetToken = null;

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

const verificationPanel =
    document.getElementById("verification-panel");

const forgotPasswordPanel =
    document.getElementById("forgot-password-panel");

const resetPasswordPanel =
    document.getElementById("reset-password-panel");


function getAccessToken() {
    return sessionStorage.getItem(TOKEN_KEY);
}


function saveAccessToken(token) {
    sessionStorage.setItem(TOKEN_KEY, token);
}


function clearAccessToken() {
    sessionStorage.removeItem(TOKEN_KEY);
}


async function refreshAccessToken() {
    const response = await fetch(
        "/api/refresh",
        {
            method: "POST",
            credentials: "include"
        }
    );

    if (!response.ok) {
        clearAccessToken();
        return null;
    }

    const data = await response.json();
    saveAccessToken(data.access_token);

    return data.access_token;
}


async function authenticatedFetch(url, options = {}) {
    let token = getAccessToken();

    if (!token) {
        token = await refreshAccessToken();

        if (!token) {
            return null;
        }
    }

    const headers = new Headers(
        options.headers || {}
    );

    headers.set(
        "Authorization",
        `Bearer ${token}`
    );

    let response = await fetch(
        url,
        {
            ...options,
            headers,
            credentials: "include"
        }
    );

    if (response.status === 401) {
        token = await refreshAccessToken();

        if (!token) {
            return response;
        }

        headers.set(
            "Authorization",
            `Bearer ${token}`
        );

        response = await fetch(
            url,
            {
                ...options,
                headers,
                credentials: "include"
            }
        );
    }

    return response;
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
    verificationPanel.hidden = true;
    forgotPasswordPanel.hidden = true;
    resetPasswordPanel.hidden = true;
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


function showVerificationPanel(email) {
    document.getElementById(
        "verification-email"
    ).textContent = email;

    document.getElementById(
        "verification-message"
    ).textContent =
        "Check your email for the verification link.";

    openAuthPanel(verificationPanel);
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
    const response = await authenticatedFetch(
        "/api/users/me"
    );

    if (!response || !response.ok) {
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
            body: formData,
            credentials: "include"
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
    .getElementById("forgot-password-button")
    .addEventListener(
        "click",
        () => {
            document.getElementById(
                "forgot-password-message"
            ).textContent = "";

            openAuthPanel(forgotPasswordPanel);
        }
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
                "profile-email"
            ).textContent =
                currentUser.email || "Not set";

            document.getElementById(
                "profile-message"
            ).textContent = "";

            document.getElementById(
                "change-email-message"
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
    .getElementById("verification-to-login")
    .addEventListener(
        "click",
        () => openAuthPanel(loginPanel)
    );


document
    .getElementById("forgot-password-to-login")
    .addEventListener(
        "click",
        () => openAuthPanel(loginPanel)
    );


document
    .getElementById("logout-button")
    .addEventListener(
        "click",
        async () => {
            try {
                await fetch(
                    "/api/logout",
                    {
                        method: "POST",
                        credentials: "include"
                    }
                );
            } finally {
                clearAccessToken();
                showGuestAccount();
                closeAccountDropdown();
            }
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

            const email =
                document.getElementById(
                    "register-email"
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
                            email,
                            password,
                            preferred_city:
                                preferredCity
                        })
                    }
                );

                if (!response.ok) {
                    if (response.status === 409) {
                        throw new Error(
                            "Username or email is already registered."
                        );
                    }

                    throw new Error(
                        "Could not create account."
                    );
                }

                message.textContent = "";

                document.getElementById(
                    "register-form"
                ).reset();

                showVerificationPanel(email);

            } catch (error) {
                message.textContent =
                    error.message;
            }
        }
    );


document
    .getElementById("forgot-password-form")
    .addEventListener(
        "submit",
        async (event) => {
            event.preventDefault();

            const email =
                document.getElementById(
                    "forgot-password-email"
                ).value.trim();

            const message =
                document.getElementById(
                    "forgot-password-message"
                );

            message.textContent =
                "Sending reset instructions...";

            try {
                const response = await fetch(
                    "/api/password-reset/request",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type":
                                "application/json"
                        },
                        body: JSON.stringify({
                            email
                        })
                    }
                );

                if (!response.ok) {
                    throw new Error(
                        "Could not request password reset."
                    );
                }

                message.textContent =
                    "If a verified account exists for that email, " +
                    "password reset instructions have been sent.";

            } catch (error) {
                message.textContent =
                    error.message;
            }
        }
    );


document
    .getElementById("resend-verification-button")
    .addEventListener(
        "click",
        async () => {
            const email =
                document.getElementById(
                    "verification-email"
                ).textContent.trim();

            const message =
                document.getElementById(
                    "verification-message"
                );

            message.textContent = "Sending...";

            try {
                const response = await fetch(
                    "/api/email/resend-verification",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type":
                                "application/json"
                        },
                        body: JSON.stringify({
                            email
                        })
                    }
                );

                if (!response.ok) {
                    throw new Error(
                        "Could not resend verification email."
                    );
                }

                message.textContent =
                    "Check your email. A new verification link was sent.";

            } catch (error) {
                message.textContent =
                    error.message;
            }
        }
    );


document
    .getElementById("reset-password-form")
    .addEventListener(
        "submit",
        async (event) => {
            event.preventDefault();

            const message =
                document.getElementById(
                    "reset-password-message"
                );

            const newPassword =
                document.getElementById(
                    "reset-password-new"
                ).value;

            const confirmation =
                document.getElementById(
                    "reset-password-confirm"
                ).value;

            if (newPassword !== confirmation) {
                message.textContent =
                    "Passwords do not match.";
                return;
            }

            if (!passwordResetToken) {
                message.textContent =
                    "Password reset link is invalid or expired.";
                return;
            }

            message.textContent =
                "Resetting password...";

            try {
                const response = await fetch(
                    "/api/password-reset/confirm",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type":
                                "application/json"
                        },
                        body: JSON.stringify({
                            token: passwordResetToken,
                            new_password: newPassword
                        })
                    }
                );

                if (!response.ok) {
                    throw new Error(
                        "Password reset link is invalid or expired."
                    );
                }

                passwordResetToken = null;

                document.getElementById(
                    "reset-password-form"
                ).reset();

                document.getElementById(
                    "login-message"
                ).textContent =
                    "Password reset successful. You can now log in.";

                openAuthPanel(loginPanel);

            } catch (error) {
                message.textContent =
                    error.message;
            }
        }
    );


document
    .getElementById("change-email-form")
    .addEventListener(
        "submit",
        async (event) => {
            event.preventDefault();

            const newEmail =
                document.getElementById(
                    "change-email-new"
                ).value.trim();

            const currentPassword =
                document.getElementById(
                    "change-email-password"
                ).value;

            const message =
                document.getElementById(
                    "change-email-message"
                );

            message.textContent =
                "Sending verification email...";

            try {
                const response =
                    await authenticatedFetch(
                        "/api/users/me/email",
                        {
                            method: "POST",
                            headers: {
                                "Content-Type":
                                    "application/json"
                            },
                            body: JSON.stringify({
                                new_email: newEmail,
                                current_password:
                                    currentPassword
                            })
                        }
                    );

                if (!response) {
                    throw new Error(
                        "Your session has expired. Please log in again."
                    );
                }

                if (!response.ok) {
                    if (response.status === 409) {
                        throw new Error(
                            "That email address is already registered."
                        );
                    }

                    if (response.status === 400) {
                        throw new Error(
                            "Current password is incorrect."
                        );
                    }

                    throw new Error(
                        "Could not start email change."
                    );
                }

                document.getElementById(
                    "change-email-form"
                ).reset();

                message.textContent =
                    "Check your new email to confirm the change.";

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
                const response =
                    await authenticatedFetch(
                        "/api/users/me",
                        {
                            method: "PATCH",
                            headers: {
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


function handlePasswordResetLink() {
    const params =
        new URLSearchParams(window.location.search);

    const token =
        params.get("reset_password_token");

    if (!token) {
        return false;
    }

    passwordResetToken = token;

    params.delete("reset_password_token");

    const remainingQuery =
        params.toString();

    const cleanUrl =
        window.location.pathname +
        (remainingQuery ? `?${remainingQuery}` : "") +
        window.location.hash;

    history.replaceState(
        {},
        document.title,
        cleanUrl
    );

    document.getElementById(
        "reset-password-message"
    ).textContent = "";

    openAuthPanel(resetPasswordPanel);

    return true;
}


async function handleEmailChangeLink() {
    const params =
        new URLSearchParams(window.location.search);

    const token =
        params.get("change_email_token");

    if (!token) {
        return false;
    }

    params.delete("change_email_token");

    const remainingQuery =
        params.toString();

    const cleanUrl =
        window.location.pathname +
        (remainingQuery ? `?${remainingQuery}` : "") +
        window.location.hash;

    history.replaceState(
        {},
        document.title,
        cleanUrl
    );

    try {
        const response = await fetch(
            "/api/email/confirm-change",
            {
                method: "POST",
                headers: {
                    "Content-Type":
                        "application/json"
                },
                body: JSON.stringify({
                    token
                })
            }
        );

        if (!response.ok) {
            throw new Error(
                "Email change link is invalid or expired."
            );
        }

        document.getElementById(
            "login-message"
        ).textContent =
            "Email changed successfully.";

        openAuthPanel(loginPanel);

    } catch (error) {
        document.getElementById(
            "login-message"
        ).textContent =
            error.message;

        openAuthPanel(loginPanel);
    }

    return true;
}


async function handleEmailVerificationLink() {
    const params =
        new URLSearchParams(window.location.search);

    const token =
        params.get("verify_email_token");

    if (!token) {
        return;
    }

    params.delete("verify_email_token");

    const remainingQuery =
        params.toString();

    const cleanUrl =
        window.location.pathname +
        (remainingQuery ? `?${remainingQuery}` : "") +
        window.location.hash;

    history.replaceState(
        {},
        document.title,
        cleanUrl
    );

    try {
        const response = await fetch(
            "/api/email/verify",
            {
                method: "POST",
                headers: {
                    "Content-Type":
                        "application/json"
                },
                body: JSON.stringify({
                    token
                })
            }
        );

        if (!response.ok) {
            throw new Error(
                "Verification link is invalid or expired."
            );
        }

        document.getElementById(
            "login-message"
        ).textContent =
            "Email verified. You can now log in.";

        openAuthPanel(loginPanel);

    } catch (error) {
        document.getElementById(
            "login-message"
        ).textContent =
            error.message;

        openAuthPanel(loginPanel);
    }
}


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


async function initializeAuth() {
    showGuestAccount();

    const handlingPasswordReset =
        handlePasswordResetLink();

    if (handlingPasswordReset) {
        return;
    }

    const handlingEmailChange =
        await handleEmailChangeLink();

    if (handlingEmailChange) {
        return;
    }

    await handleEmailVerificationLink();
    await restoreSession();
}


initializeAuth();
