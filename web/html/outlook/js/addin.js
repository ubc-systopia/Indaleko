const LOGIN_URL = 'https://activitycontext.work/outlook/login.php';
console.log(`LOGIN_URL === ${LOGIN_URL}`);

const sessionStorageForOutlook = {
    accessToken: null,
    setItem: function(token) {
        this.accessToken = token;
    },
    getItem: function() {
        return this.accessToken;
    }
};
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
        console.log('On send handler called...');
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
                            console.log(`getting fullLink....`);
                            let oneDriveData = await expandOneDriveUrlAsync(link);
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
                            console.log("Email ID: " + result.value);
                        } else {
                            console.error("Error getting email ID: " + result.error.message);
                        }
                    });
                
                    // Get sender's email address
                    item.from.getAsync(function(result) {
                        if (result.status === Office.AsyncResultStatus.Succeeded) {
                            var senderEmailAddress = result.value.emailAddress;
                            finalData.senderEmailAddress = senderEmailAddress;
                            console.log("Sender's Email Address: " + senderEmailAddress);
                        } else {
                            console.error("Error getting sender's email address: " + result.error.message);
                        }
                    });

                    item.subject.getAsync(function(result) {
                        if (result.status === Office.AsyncResultStatus.Succeeded) {
                            var subject = result.value;
                            finalData.subject = subject;
                            console.log("Subject: " + subject);
                        } else {
                            console.error("Error getting sender's subject: " + result.error.message);
                        }
                    });
                
                    // Get recipient's email addresses
                    item.to.getAsync(function(result) {
                        if (result.status === Office.AsyncResultStatus.Succeeded) {
                            var recipientEmailAddresses = result.value.map(function(recipient) {
                                return recipient.emailAddress;
                            });
                            finalData.recipientEmailAddresses = recipientEmailAddresses;
                            console.log(finalData); 
                            sendDataToServer(finalData);
                            event.completed({ allowEvent: true });
                            console.log("Recipient(s) Email Address(es): " + recipientEmailAddresses.join(", "));
                        } else {
                            console.error("Error getting recipient's email addresses: " + result.error.message);
                        }
                    });
                });
            } else {
                console.log("Failed to retrieve attachments: " + result.error.message);
                event.completed({ allowEvent: true });
            }
        });
    });
}


function expandOneDriveUrl(shortenedUrl) {
    return new Promise((resolve, reject) => {
        document.getElementById("authResult").innerHTML = JSON.stringify(sessionStorageForOutlook);
        const proxyUrl = `https://activitycontext.work/outlook/onedrive.php?link=${shortenedUrl}&token=${sessionStorageForOutlook.getItem("accessToken")}`;
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





async function expandOneDriveUrlAsync(shortenedUrl) {
    try {
        const expandedUrl = await expandOneDriveUrl(shortenedUrl);
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
        console.log(`Access Token ===== ${sessionStorageForOutlook.getItem("accessToken")}`);
        //return sessionStorageForOutlook.getItem("accessToken") !== null;
        return false;
    }

    // Function to handle authentication
    function authenticate() {
        if (isOutlookDesktopClient()) {
            authenticateDesktop();
        } else {
            authenticateWeb();
        }
    }
    
    function authenticateWeb() {
        const CODE_VERIFIER = generateCodeVerifier(128);
        // Construct the authorization URL with necessary parameters
        generateCodeChallenge(CODE_VERIFIER)
            .then((codeChallenge) => {
                var authorizationUrl = `${LOGIN_URL}?code_challenge=${codeChallenge}&code_verifier=${CODE_VERIFIER}&view=OW`;
    
                // Open a new window with the authorization URL
                var authWindow = window.open(authorizationUrl, "_blank");
    
                // Listen for changes in the new window's URL
                var interval = setInterval(function () {
                    try {
                        // Check if the new window's URL contains the authorization code
                        if (authWindow.location.href.indexOf("?token=") !== -1) {
                            clearInterval(interval);
                            authWindow.close();
    
                            // Extract the authorization code from the URL
                            var accessToken = authWindow.location.href.split("?token=")[1];
                            
                            // Store the access token in session storage
                            sessionStorageForOutlook.setItem(accessToken);
    
                            // Update UI to indicate successful authentication
                            updateUIAfterAuthentication(accessToken);
                        }
                    } catch (error) {
                        // Suppress any errors due to cross-origin security restrictions
                    }
                }, 500);
            })
            .catch((error) => {
                console.error("Error during authentication:", error);
            });
    }
    
    function authenticateDesktop() {
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
                                xhr.open("GET", "https://activitycontext.work/outlook/retrieve.php", true);
                                xhr.onreadystatechange = function () {
                                    if (xhr.readyState == 4 && xhr.status == 200) {
                                        var response = JSON.parse(xhr.responseText);
                                        if(response.od_token) {
                                            document.getElementById("authResult").insertAdjacentHTML('beforeend', response.od_token);
                                            clearInterval(interval);
                                            sessionStorageForOutlook.setItem(response.od_token);

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
        //document.getElementById("token").innerHTML = `Token found ${accessToken}`;
    }
    
    // Function to check if the add-in is running in the Outlook desktop client
    function isOutlookDesktopClient() {
        // Check if the Office.context.mailbox.diagnostics object is available
        // This object is only available in the desktop client
        return Office.context.mailbox.diagnostics !== undefined;
    }
    

    if (isAuthenticated()) {
        document.getElementById("authenticateButton").innerHTML = "Re-Login";
        document.getElementById("authResult").innerHTML = 'You are connected with Graph API!';
    } 
    console.log('we are here...');
    document.getElementById("authenticateButton").addEventListener("click", authenticate);
});