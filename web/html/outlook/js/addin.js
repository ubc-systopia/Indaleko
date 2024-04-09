const LOGIN_URL = 'https://activitycontext.work/outlook/login.php';

let ACCESS_TOKEN = null;


// Generate a random code verifier
function generateCodeVerifier(length) {
    var charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";
    var verifier = "";
    for (var i = 0; i < length; i++) {
        verifier += charset.charAt(Math.floor(Math.random() * charset.length));
    }
    return verifier;
}

// Generate the code challenge from the code verifier
async function generateCodeChallenge(codeVerifier) {
    // Encode the code verifier to a Uint8Array
    var buffer = new TextEncoder().encode(codeVerifier);

    // Generate the SHA-256 hash of the code verifier
    var digestBuffer = await crypto.subtle.digest('SHA-256', buffer);

    // Convert the digest buffer to a base64url encoded string
    var codeChallenge = base64urlencode(digestBuffer);
    return codeChallenge;
}

// Base64 URL-encode function
function base64urlencode(buffer) {
    var encoded = String.fromCharCode.apply(null, new Uint8Array(buffer));
    return btoa(encoded)
        .replace(/\+/g, "-")
        .replace(/\//g, "_")
        .replace(/=/g, "");
}

// SHA-256 hash function
async function sha256(buffer) {
    const digestBuffer = await crypto.subtle.digest('SHA-256', buffer);
    return digestBuffer;
}

function objectToUrlEncoded(object) {
   return Object.keys(object).map(key => encodeURIComponent(key) + '=' + encodeURIComponent(object[key])).join('&');
}

function onSendHandler(event) {
    Office.onReady(function () {
        const tokenKey = getAccessToken();
        if(tokenKey === null || !tokenKey) {
            try {
                Office.context.mailbox.item.notificationMessages.addAsync('NoSend', { type: 'errorMessage', message: 'Please login with Graph API in order to send mail' });
            } catch(error) {
                //Error in case of outlook desktop
            }
            event.completed({ allowEvent: false, errorMessage: 'Validation failed: Your error message here' });
        } else {
            // Retrieve attachments
            const finalData = {
                emailId: null,
                subject: null,
                senderEmailAddress: null,
                recipientEmailAddresses: null,
                attachments: null
            };
            Office.context.mailbox.item.getAttachmentsAsync(function (result) {
                
                if (result.status === Office.AsyncResultStatus.Succeeded) {
                    var attachments = result.value;
                    var dataToSend = []; // Array to hold attachment and OneDrive link data
                    // Process regular attachments
                    attachments.forEach(function (attachment) {
                        var attachmentData = {
                            fileName: attachment.name,
                            attachmentClass: 'regular',
                            metas: attachment
                        };
                        dataToSend.push(attachmentData);
                    });

                    // Retrieve HTML body of the email
                    Office.context.mailbox.item.body.getAsync("html", async function (result) {
                        if (result.status === Office.AsyncResultStatus.Succeeded) {
                            var emailBody = result.value;
                            // Check for OneDrive links in the HTML body
                            var oneDriveLinks = extractOneDriveLinks(emailBody);
                            for(let i=0; i < oneDriveLinks.length; i++) {
                                let link = oneDriveLinks[i];
                                let oneDriveData = await expandOneDriveUrlAsync(link, tokenKey);
                                dataToSend.push(oneDriveData);
                            }
                            finalData.attachments = dataToSend;
                        } else {
                            console.error("Failed to retrieve email body: " + result.error.message);
                        }

                        const item = Office.context.mailbox.item;
                        
                        item.getItemIdAsync(function(result) {
                            if (result.status === Office.AsyncResultStatus.Succeeded) {
                                finalData.emailId = result.value;
                                // Get sender's email address
                                item.from.getAsync(function(result) {
                                    if (result.status === Office.AsyncResultStatus.Succeeded) {
                                        var senderEmailAddress = result.value.emailAddress;
                                        finalData.senderEmailAddress = senderEmailAddress;
                                    } else {
                                    }
                                });

                                item.subject.getAsync(function(result) {
                                    if (result.status === Office.AsyncResultStatus.Succeeded) {
                                        var subject = result.value;
                                        finalData.subject = subject;
                                    } else {
                                    }
                                });
                            
                                // Get recipient's email addresses
                                item.to.getAsync(async function(result) {
                                    if (result.status === Office.AsyncResultStatus.Succeeded) {
                                        var recipientEmailAddresses = result.value.map(function(recipient) {
                                            return recipient.emailAddress;
                                        });
                                        finalData.recipientEmailAddresses = recipientEmailAddresses;
                                        sendDataToServer(finalData);
                                        event.completed({ allowEvent: true });
                                    } else {
                                    }
                                });
                            }
                        });
                    });
                } else {
                    event.completed({ allowEvent: true });
                }
            });
        }
    });
}

function saveAccessToken(token) {
    localStorage.setItem('tokenKey', token);
}

function getAccessToken() {
    return localStorage.getItem('tokenKey');
}


async function expandOneDriveUrl(shortenedUrl, token) {
    return new Promise((resolve, reject) => {
        const proxyUrl = `https://activitycontext.work/outlook/onedrive.php?link=${shortenedUrl}&token=${token}`;
        const xhr = new XMLHttpRequest();
        xhr.open('GET', proxyUrl);
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                if (xhr.status === 200) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (error) {
                        reject(new Error('Error parsing response: ' + error.message));
                    }
                } else {
                    reject(new Error('Failed to fetch URL. Status code: ' + xhr.status));
                }
            }
        };
        xhr.onerror = function() {
            reject(new Error('Error expanding OneDrive URL'));
        };
        xhr.send();
    });
}

async function expandOneDriveUrlAsync(shortenedUrl, tokenKey) {
    try {
        const expandedUrl = await expandOneDriveUrl(shortenedUrl, tokenKey);
        return expandedUrl;
    } catch (error) {
        console.error('Error expanding OneDrive URL:', error);
        return null;
    }
}


// Function to extract OneDrive links from HTML content
function extractOneDriveLinks(htmlContent) {
    var oneDriveLinks = [];
    var parser = new DOMParser();
    var doc = parser.parseFromString(htmlContent, "text/html");
    var links = doc.querySelectorAll("a[href*='1drv.ms']");
    links.forEach(function (link) {
        oneDriveLinks.push(link.getAttribute("href"));
    });
    return oneDriveLinks;
}

function sendDataToServer(data) {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "processData.php", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onreadystatechange = function () {
        if (xhr.readyState === XMLHttpRequest.DONE) {
            if (xhr.status === 200) {
                console.log("Data sent successfully.");
            } else {
                console.error("Failed to send data: " + xhr.statusText);
            }
        }
    };
    xhr.send(JSON.stringify(data));
}

Office.onReady(function () {
    // Function to check if the user is authenticated
    function isAuthenticated() {
        return false;
    }

    // Function to handle authentication
    function authenticate() {
        saveAccessToken(null);
        authenticateGraph();
    }
    
    function authenticateGraph() {
        // Construct the authorization URL with necessary parameters
        const CODE_VERIFIER = generateCodeVerifier(128);
        // Construct the authorization URL with necessary parameters
        generateCodeChallenge(CODE_VERIFIER)
            .then((codeChallenge) => {
                var authorizationUrl = `${LOGIN_URL}?code_challenge=${codeChallenge}&code_verifier=${CODE_VERIFIER}`;
                // Open a dialog window within Outlook desktop client
                Office.context.ui.displayDialogAsync(authorizationUrl, { height: 40, width: 40 }, function (result) {
                    if (result.status === Office.AsyncResultStatus.Succeeded) {
                        var dialog = result.value;
                        document.getElementById("authResult").innerHTML = `Result ==== ${JSON.stringify(result)}`;
                        // Add event listener for dialog message event
                        if(Object.keys(dialog).length > 0) {
                            var interval = setInterval(function () {
                                var xhr = new XMLHttpRequest();
                                xhr.open("GET", `https://activitycontext.work/outlook/retrieve.php?code=${CODE_VERIFIER}`, true);
                                xhr.onreadystatechange = function () {
                                    if (xhr.readyState == 4 && xhr.status == 200) {
                                        var response = JSON.parse(xhr.responseText);
                                        if(response.od_token) {
                                            clearInterval(interval);
                                            saveAccessToken(response.od_token); 
                                            // Update UI to indicate successful authentication
                                            updateUIAfterAuthentication(response.od_token);
                                            dialog.close();
                                        } else {
                                            document.getElementById("authResult").insertAdjacentHTML('beforeend', `ElseData == ${response}`);
                                        } 
                                    }
                                };
                                xhr.send();
                            }, 1500);
                        } else {
                            document.getElementById("authResult").innerHTML = `Dialog is empty or invalid`;
                        }
                    } else {
                        // Handle error
                        console.error("Error displaying dialog:", result.error.message);
                        document.getElementById("authResult").innerHTML = `ErrorReult is ${result.error.message}`;
                    }
                });
            })
            .catch((error) => {
                console.error("Error during authentication:", error);
            });
    }
    
    // Function to update UI after successful authentication
    function updateUIAfterAuthentication(accessToken) {
        document.getElementById("authenticateButton").innerHTML = "Re-Login";
        document.getElementById("authResult").innerHTML = 'You are connected with Graph API!';
    }
    if (isAuthenticated()) {
        document.getElementById("authenticateButton").innerHTML = "Re-Login";
        document.getElementById("authResult").innerHTML = 'You are connected with Graph API!';
    }
    document.getElementById("authenticateButton").addEventListener("click", authenticate);
});