"""
This module implements an Outlook email file sharing collector for Indaleko.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import json
import logging
import os
import sys
import threading
import time
import uuid

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request
from pyngrok import ngrok


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
import builtins
import contextlib

from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.collaboration.collaboration_base import CollaborationCollector
from activity.collectors.collaboration.data_models.email_file_share import (
    EmailFileShareData,
)
from activity.collectors.collaboration.data_models.shared_file import SharedFileData


# pylint: enable=wrong-import-position


class OutlookFileShareCollector(CollaborationCollector):
    """
    Outlook file sharing collector for Indaleko.

    This collector sets up a local web service with ngrok tunneling to receive
    data from an Outlook add-in when files are shared via email. It tracks both
    regular email attachments and OneDrive/SharePoint links shared in emails.
    """

    def __init__(
        self,
        config_dir: str = "./config",
        data_dir: str = "./outlook_data",
        port: int = 5000,
        manifest_dir: str | None = None,
        **kwargs,
    ) -> None:
        """
        Initialize the Outlook file sharing collector.

        Args:
            config_dir: Directory for configuration files
            data_dir: Directory for storing collected data
            port: Port for the local web server
            manifest_dir: Directory to store the generated manifest file
            **kwargs: Additional arguments
        """
        super().__init__(**kwargs)

        # Set up basic properties
        self._provider_id = uuid.UUID("72a81b94-5e3c-4d6f-8792-0a48c9d6e107")
        self._name = "Outlook File Share Collector"
        self._description = "Collects file sharing activity from Outlook emails"

        # Set up logging
        self.logger = logging.getLogger("OutlookFileShareCollector")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Directory setup
        self.config_dir = Path(config_dir)
        self.data_dir = Path(data_dir)
        self.manifest_dir = Path(manifest_dir) if manifest_dir else Path("./manifest")

        # Create directories if they don't exist
        self.config_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        self.manifest_dir.mkdir(exist_ok=True)

        # Web server settings
        self.port = port
        self.ngrok_tunnel = None
        self.public_url = None

        # Storage for collected data
        self.file_shares = []

        # Server thread
        self.server_thread = None
        self.flask_app = None
        self.server_running = False

    def start_ngrok_tunnel(self) -> str:
        """
        Start an ngrok tunnel to make the local server publicly accessible.

        Returns:
            Public URL of the tunnel
        """
        try:
            # Start ngrok tunnel
            tunnel = ngrok.connect(self.port)
            self.ngrok_tunnel = tunnel
            self.public_url = tunnel.public_url

            if self.public_url.startswith("http://"):
                # Force HTTPS version for Microsoft add-ins
                self.public_url = "https://" + self.public_url[7:]

            self.logger.info(f"ngrok tunnel started at: {self.public_url}")
            return self.public_url
        except Exception as e:
            self.logger.exception(f"Failed to start ngrok tunnel: {e}")
            raise

    def stop_ngrok_tunnel(self) -> None:
        """Stop the ngrok tunnel."""
        if self.ngrok_tunnel:
            try:
                ngrok.disconnect(self.ngrok_tunnel.public_url)
                self.logger.info("ngrok tunnel stopped")
            except Exception as e:
                self.logger.exception(f"Error stopping ngrok tunnel: {e}")
            self.ngrok_tunnel = None
            self.public_url = None

    def generate_manifest(self) -> str:
        """
        Generate an Outlook add-in manifest file.

        Returns:
            Path to the generated manifest file
        """
        manifest_path = self.manifest_dir / "outlook-addin-manifest.xml"

        # Ensure we have a public URL
        if not self.public_url:
            raise ValueError("Cannot generate manifest without a public URL")

        # Base URL without trailing slash
        base_url = self.public_url.rstrip("/")

        manifest_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<OfficeApp
    xmlns="http://schemas.microsoft.com/office/appforoffice/1.1"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:bt="http://schemas.microsoft.com/office/officeappbasictypes/1.0"
    xmlns:mailappor="http://schemas.microsoft.com/office/mailappversionoverrides/1.0" xsi:type="MailApp">
    <Id>{self._provider_id}</Id>
    <Version>1.0.0</Version>
    <ProviderName>Indaleko</ProviderName>
    <DefaultLocale>en-US</DefaultLocale>
    <DisplayName DefaultValue="Indaleko File Tracker"/>
    <Description DefaultValue="Tracks files shared through Outlook"/>
    <IconUrl DefaultValue="{base_url}/static/icon-32.png"/>
    <HighResolutionIconUrl DefaultValue="{base_url}/static/icon-80.png"/>
    <SupportUrl DefaultValue="{base_url}/help"/>
    <AppDomains>
        <AppDomain>{base_url}</AppDomain>
    </AppDomains>
    <Hosts>
        <Host Name="Mailbox"/>
    </Hosts>
    <Requirements>
        <Sets>
            <Set Name="Mailbox" MinVersion="1.3"/>
        </Sets>
    </Requirements>
    <FormSettings>
        <Form xsi:type="ItemRead">
            <DesktopSettings>
                <SourceLocation DefaultValue="{base_url}/taskpane"/>
                <RequestedHeight>250</RequestedHeight>
            </DesktopSettings>
        </Form>
    </FormSettings>
    <Permissions>ReadWriteItem</Permissions>
    <Rule xsi:type="RuleCollection" Mode="Or">
        <Rule xsi:type="ItemIs" ItemType="Message" FormType="ReadOrEdit"/></Rule>
    <DisableEntityHighlighting>false</DisableEntityHighlighting>
    <VersionOverrides
        xmlns="http://schemas.microsoft.com/office/mailappversionoverrides" xsi:type="VersionOverridesV1_0">
        <VersionOverrides
            xmlns="http://schemas.microsoft.com/office/mailappversionoverrides/1.1" xsi:type="VersionOverridesV1_1">
            <Requirements>
                <bt:Sets DefaultMinVersion="1.3">
                    <bt:Set Name="Mailbox"/>
                </bt:Sets>
            </Requirements>
            <Hosts>
                <Host xsi:type="MailHost">
                    <DesktopFormFactor>
                        <FunctionFile resid="Taskpane.Url" />
                        <ExtensionPoint xsi:type="Events">
                            <Event Type="ItemSend" FunctionExecution="synchronous" FunctionName="onSendHandler" />
                        </ExtensionPoint>
                        <ExtensionPoint xsi:type="MessageComposeCommandSurface">
                            <OfficeTab id="TabDefault">
                                <Group id="msgComposeGroup">
                                    <Label resid="GroupLabel"/>
                                    <Control xsi:type="Button" id="msgComposeOpenPaneButton">
                                        <Label resid="TaskpaneButton.Label"/>
                                        <Supertip>
                                            <Title resid="TaskpaneButton.Label"/>
                                            <Description resid="TaskpaneButton.Tooltip"/>
                                        </Supertip>
                                        <Icon>
                                            <bt:Image size="16" resid="Icon.16x16"/>
                                            <bt:Image size="32" resid="Icon.32x32"/>
                                            <bt:Image size="80" resid="Icon.80x80"/>
                                        </Icon>
                                        <Action xsi:type="ShowTaskpane">
                                            <SourceLocation resid="Taskpane.Url"/>
                                        </Action>
                                    </Control>
                                </Group>
                            </OfficeTab>
                        </ExtensionPoint>
                    </DesktopFormFactor>
                </Host>
            </Hosts>
            <Resources>
                <bt:Images>
                    <bt:Image id="Icon.16x16" DefaultValue="{base_url}/static/icon-16.png"/>
                    <bt:Image id="Icon.32x32" DefaultValue="{base_url}/static/icon-32.png"/>
                    <bt:Image id="Icon.80x80" DefaultValue="{base_url}/static/icon-80.png"/>
                </bt:Images>
                <bt:Urls>
                    <bt:Url id="Taskpane.Url" DefaultValue="{base_url}/taskpane"/>
                </bt:Urls>
                <bt:ShortStrings>
                    <bt:String id="GroupLabel" DefaultValue="Indaleko"/>
                    <bt:String id="TaskpaneButton.Label" DefaultValue="Track Files"/>
                </bt:ShortStrings>
                <bt:LongStrings>
                    <bt:String id="TaskpaneButton.Tooltip" DefaultValue="Track files shared in this email"/>
                </bt:LongStrings>
            </Resources>
        </VersionOverrides>
    </VersionOverrides>
</OfficeApp>
"""

        # Write manifest file
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(manifest_content)

        self.logger.info(f"Generated Outlook add-in manifest at: {manifest_path}")
        return str(manifest_path)

    def create_flask_app(self) -> Flask:
        """
        Create a Flask app for the Outlook add-in web server.

        Returns:
            Flask application
        """
        app = Flask("Indaleko_Outlook_Addin")
        app.secret_key = str(uuid.uuid4())

        # Static files directory
        os.makedirs(os.path.join(os.path.dirname(__file__), "static"), exist_ok=True)

        @app.route("/")
        def index() -> str:
            """Home page."""
            return f"""
            <html>
            <head>
                <title>Indaleko Outlook Add-in Server</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                    h1 {{ color: #333; }}
                    .container {{ max-width: 800px; margin: 0 auto; }}
                    .info {{ background-color: #f5f5f5; padding: 20px; border-radius: 5px; }}
                    .manifest {{ margin-top: 20px; background-color: #e9f7ff; padding: 20px; border-radius: 5px; }}
                    pre {{ background-color: #f0f0f0; padding: 10px; overflow-x: auto; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Indaleko Outlook Add-in Server</h1>
                    <div class="info">
                        <p>Server is running at: <strong>{self.public_url}</strong></p>
                        <p>To use this add-in, install the manifest file in Outlook.</p>
                    </div>
                    <div class="manifest">
                        <h2>Manifest</h2>
                        <p>Manifest file is available at: <a href="/manifest" target="_blank">{self.public_url}/manifest</a></p>
                    </div>
                </div>
            </body>
            </html>
            """

        @app.route("/manifest")
        def manifest():
            """Serve the manifest file."""
            manifest_path = self.generate_manifest()
            with open(manifest_path, encoding="utf-8") as f:
                content = f.read()
            return content, 200, {"Content-Type": "application/xml"}

        @app.route("/taskpane")
        def taskpane() -> str:
            """Serve the taskpane.html content."""
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Indaleko File Tracker</title>
                <script src="https://appsforoffice.microsoft.com/lib/1/hosted/office.js"></script>
                <script src="{self.public_url}/static/addin.js" type="text/javascript"></script>
                <style type="text/css">
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background-color: #f0f0f0;
                        margin: 0;
                        padding: 15px;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background-color: #fff;
                        padding: 20px;
                        border-radius: 8px;
                        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                    }}
                    h1 {{
                        color: #333;
                        font-size: 18px;
                        margin-top: 0;
                    }}
                    p {{
                        color: #555;
                        font-size: 14px;
                        line-height: 1.5;
                    }}
                    .status {{
                        margin-top: 15px;
                        padding: 10px;
                        background-color: #f9f9f9;
                        border-radius: 4px;
                        font-size: 14px;
                    }}
                    .success {{
                        color: #2e7d32;
                        background-color: #e8f5e9;
                    }}
                    .error {{
                        color: #c62828;
                        background-color: #ffebee;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Indaleko File Tracker</h1>
                    <p>This add-in tracks files shared in your emails to help you find and organize them later.</p>
                    <p>When sending an email with attachments or links, the file information will be automatically collected for Indaleko.</p>
                    <div id="status" class="status">Ready to track shared files...</div>
                </div>
            </body>
            </html>
            """

        @app.route("/static/addin.js")
        def addin_js() -> str:
            """Serve the add-in JavaScript."""
            return f"""
            // Indaleko Outlook Add-in

            // Will be run when email is sent
            function onSendHandler(event) {{
                Office.onReady(function () {{
                    try {{
                        // Get email metadata and attachments
                        collectEmailData(event);
                    }} catch (error) {{
                        console.error("Error in onSendHandler:", error);
                        // Don't block the send
                        event.completed({{ allowEvent: true }});
                    }}
                }});
            }}

            // Collect email data including attachments and links
            function collectEmailData(event) {{
                const finalData = {{
                    emailId: null,
                    subject: null,
                    senderEmailAddress: null,
                    recipientEmailAddresses: null,
                    attachments: null,
                    timestamp: new Date().toISOString()
                }};

                // Get attachments
                Office.context.mailbox.item.getAttachmentsAsync(function(result) {{
                    if (result.status === Office.AsyncResultStatus.Succeeded) {{
                        var attachments = result.value;
                        var dataToSend = []; // Array to hold attachment data

                        // Process regular attachments
                        attachments.forEach(function(attachment) {{
                            var attachmentData = {{
                                fileName: attachment.name,
                                attachmentType: 'regular',
                                contentType: attachment.contentType,
                                size: attachment.size,
                                id: attachment.id
                            }};
                            dataToSend.push(attachmentData);
                        }});

                        // Retrieve HTML body to look for links
                        Office.context.mailbox.item.body.getAsync("html", function(result) {{
                            if (result.status === Office.AsyncResultStatus.Succeeded) {{
                                var emailBody = result.value;
                                // Extract OneDrive/SharePoint links
                                var oneDriveLinks = extractOneDriveLinks(emailBody);
                                var sharepointLinks = extractSharePointLinks(emailBody);

                                // Add OneDrive links
                                oneDriveLinks.forEach(function(link) {{
                                    dataToSend.push({{
                                        fileName: extractFileName(link),
                                        attachmentType: 'onedrive',
                                        url: link
                                    }});
                                }});

                                // Add SharePoint links
                                sharepointLinks.forEach(function(link) {{
                                    dataToSend.push({{
                                        fileName: extractFileName(link),
                                        attachmentType: 'sharepoint',
                                        url: link
                                    }});
                                }});

                                finalData.attachments = dataToSend;
                            }}

                            // Get email metadata
                            const item = Office.context.mailbox.item;

                            // Get email ID
                            item.getItemIdAsync(function(result) {{
                                if (result.status === Office.AsyncResultStatus.Succeeded) {{
                                    finalData.emailId = result.value;

                                    // Get sender's email
                                    item.from.getAsync(function(result) {{
                                        if (result.status === Office.AsyncResultStatus.Succeeded) {{
                                            finalData.senderEmailAddress = result.value.emailAddress;
                                        }}

                                        // Get subject
                                        item.subject.getAsync(function(result) {{
                                            if (result.status === Office.AsyncResultStatus.Succeeded) {{
                                                finalData.subject = result.value;
                                            }}

                                            // Get recipients
                                            item.to.getAsync(function(result) {{
                                                if (result.status === Office.AsyncResultStatus.Succeeded) {{
                                                    finalData.recipientEmailAddresses = result.value.map(function(recipient) {{
                                                        return recipient.emailAddress;
                                                    }});

                                                    // Send data to server
                                                    sendDataToServer(finalData);

                                                    // Don't block the send
                                                    event.completed({{ allowEvent: true }});
                                                }} else {{
                                                    event.completed({{ allowEvent: true }});
                                                }}
                                            }});
                                        }});
                                    }});
                                }} else {{
                                    event.completed({{ allowEvent: true }});
                                }}
                            }});
                        }});
                    }} else {{
                        event.completed({{ allowEvent: true }});
                    }}
                }});
            }}

            // Extract OneDrive links from HTML content
            function extractOneDriveLinks(htmlContent) {{
                var links = [];
                var parser = new DOMParser();
                var doc = parser.parseFromString(htmlContent, "text/html");
                var anchors = doc.querySelectorAll("a");

                anchors.forEach(function(anchor) {{
                    var href = anchor.getAttribute("href");
                    if (href && (href.includes("1drv.ms") || href.includes("onedrive.live.com"))) {{
                        links.push(href);
                    }}
                }});

                return links;
            }}

            // Extract SharePoint links from HTML content
            function extractSharePointLinks(htmlContent) {{
                var links = [];
                var parser = new DOMParser();
                var doc = parser.parseFromString(htmlContent, "text/html");
                var anchors = doc.querySelectorAll("a");

                anchors.forEach(function(anchor) {{
                    var href = anchor.getAttribute("href");
                    if (href && href.includes("sharepoint.com")) {{
                        links.push(href);
                    }}
                }});

                return links;
            }}

            // Try to extract filename from a URL
            function extractFileName(url) {{
                try {{
                    // Remove query parameters
                    var cleanUrl = url.split("?")[0];
                    // Get the last part of the path
                    var parts = cleanUrl.split("/");
                    var lastPart = parts[parts.length - 1];
                    // If it's not empty and has an extension, it's likely a filename
                    if (lastPart && lastPart.includes(".")) {{
                        return decodeURIComponent(lastPart);
                    }}
                }} catch (error) {{
                    console.error("Error extracting filename:", error);
                }}
                return "Unknown File";
            }}

            // Send data to the Indaleko server
            function sendDataToServer(data) {{
                fetch("{self.public_url}/api/email-files", {{
                    method: "POST",
                    headers: {{
                        "Content-Type": "application/json"
                    }},
                    body: JSON.stringify(data)
                }})
                .then(response => {{
                    if (!response.ok) {{
                        throw new Error("Network response was not ok");
                    }}
                    return response.json();
                }})
                .then(data => {{
                    console.log("Data sent successfully:", data);
                    updateStatus("Files tracked successfully!", "success");
                }})
                .catch(error => {{
                    console.error("Error sending data:", error);
                    updateStatus("Error tracking files. Please try again.", "error");
                }});
            }}

            // Update status message in the taskpane
            function updateStatus(message, type) {{
                var statusElement = document.getElementById("status");
                if (statusElement) {{
                    statusElement.textContent = message;
                    statusElement.className = "status " + (type || "");
                }}
            }}

            // Initialize when Office.js is ready
            Office.onReady(function() {{
                console.log("Indaleko File Tracker add-in initialized");
            }});
            """

        @app.route("/static/<path:filename>")
        def static_files(filename):
            """Serve static files."""
            if filename in ["icon-16.png", "icon-32.png", "icon-80.png"]:
                # Generate a simple colored square as an icon
                from PIL import Image, ImageDraw

                size = int(filename.split("-")[1].split(".")[0])
                img = Image.new("RGB", (size, size), color="#4B0082")  # Indigo color
                draw = ImageDraw.Draw(img)

                # Draw a white "I" in the center
                if size >= 32:
                    size // 2
                    draw.rectangle(
                        [size // 4, size // 4, 3 * size // 4, 3 * size // 4],
                        fill="#FFFFFF",
                    )
                    draw.rectangle(
                        [3 * size // 8, size // 4, 5 * size // 8, 3 * size // 4],
                        fill="#4B0082",
                    )

                # Save to a temporary file
                img_path = os.path.join(os.path.dirname(__file__), "static", filename)
                img.save(img_path)

                with open(img_path, "rb") as f:
                    return f.read(), 200, {"Content-Type": "image/png"}

            return "File not found", 404

        @app.route("/api/email-files", methods=["POST"])
        def receive_email_files():
            """API endpoint to receive email file data."""
            try:
                data = request.json
                if not data:
                    return jsonify({"error": "No data received"}), 400

                # Log the data
                self.logger.info(
                    f"Received email file data: {json.dumps(data, indent=2)}",
                )

                # Save the data
                timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
                filename = self.data_dir / f"email_files_{timestamp}.json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

                # Process the data
                self.process_email_data(data)

                return (
                    jsonify(
                        {"status": "success", "message": "Data received and processed"},
                    ),
                    200,
                )
            except Exception as e:
                self.logger.exception(f"Error processing email file data: {e}")
                return jsonify({"error": str(e)}), 500

        @app.route("/help")
        def help_page() -> str:
            """Help page for the add-in."""
            return """
            <html>
            <head>
                <title>Indaleko File Tracker - Help</title>
                <style>
                    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; line-height: 1.6; }
                    h1 { color: #333; }
                    h2 { color: #444; margin-top: 20px; }
                    .container { max-width: 800px; margin: 0 auto; }
                    .section { margin-bottom: 30px; }
                    code { background-color: #f5f5f5; padding: 2px 5px; border-radius: 3px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Indaleko File Tracker - Help</h1>

                    <div class="section">
                        <h2>About</h2>
                        <p>The Indaleko File Tracker is an Outlook add-in that tracks files shared in your emails,
                        helping you find and organize them later through the Indaleko system.</p>
                    </div>

                    <div class="section">
                        <h2>How It Works</h2>
                        <p>When you send an email containing:</p>
                        <ul>
                            <li>File attachments</li>
                            <li>OneDrive links</li>
                            <li>SharePoint links</li>
                        </ul>
                        <p>The add-in automatically captures information about these files and sends it to Indaleko's tracking system.</p>
                    </div>

                    <div class="section">
                        <h2>Privacy</h2>
                        <p>The add-in collects:</p>
                        <ul>
                            <li>Email subject</li>
                            <li>Sender and recipient email addresses</li>
                            <li>Names and URLs of shared files</li>
                        </ul>
                        <p>It does NOT collect the actual content of emails or files.</p>
                    </div>

                    <div class="section">
                        <h2>Support</h2>
                        <p>For support, please contact your Indaleko system administrator.</p>
                    </div>
                </div>
            </body>
            </html>
            """

        return app

    def process_email_data(self, data: dict) -> None:
        """
        Process received email file data.

        Args:
            data: Email data including attachments
        """
        try:
            # Extract relevant fields
            email_id = data.get("emailId")
            subject = data.get("subject")
            sender = data.get("senderEmailAddress")
            recipients = data.get("recipientEmailAddresses", [])
            timestamp = data.get("timestamp", datetime.now(UTC).isoformat())
            attachments = data.get("attachments", [])

            # Process each attachment
            for attachment in attachments:
                file_share = {
                    "email_id": email_id,
                    "subject": subject,
                    "sender": sender,
                    "recipients": recipients,
                    "timestamp": timestamp,
                    "filename": attachment.get("fileName"),
                    "attachment_type": attachment.get("attachmentType"),
                    "content_type": attachment.get("contentType"),
                    "size": attachment.get("size"),
                    "url": attachment.get("url"),
                    "id": attachment.get("id"),
                }

                # Add to the file shares list
                self.file_shares.append(file_share)

                self.logger.info(
                    f"Processed file share: {file_share['filename']} from {sender} to {recipients}",
                )
        except Exception as e:
            self.logger.exception(f"Error processing email data: {e}")

    def run_server(self) -> None:
        """Run the Flask server in a separate thread."""
        if self.server_running:
            self.logger.warning("Server is already running")
            return

        # Create Flask app
        self.flask_app = self.create_flask_app()

        # Start ngrok tunnel
        self.start_ngrok_tunnel()

        # Generate manifest
        self.generate_manifest()

        # Function to run in thread
        def run_flask() -> None:
            self.flask_app.run(host="127.0.0.1", port=self.port)

        # Start server in thread
        self.server_thread = threading.Thread(target=run_flask)
        self.server_thread.daemon = True
        self.server_thread.start()

        self.server_running = True
        self.logger.info(
            f"Server running at http://127.0.0.1:{self.port} with public URL {self.public_url}",
        )

    def stop_server(self) -> None:
        """Stop the Flask server and ngrok tunnel."""
        if not self.server_running:
            self.logger.warning("Server is not running")
            return

        # Stop ngrok tunnel
        self.stop_ngrok_tunnel()

        # Stop Flask server
        if self.server_thread and self.server_thread.is_alive():
            # This is a bit hacky but works to stop Flask in a thread
            os.kill(os.getpid(), 15)

        self.server_running = False
        self.logger.info("Server stopped")

    def get_file_shares(self) -> list[dict]:
        """
        Get all collected file shares.

        Returns:
            List of file share data
        """
        return self.file_shares

    def clear_file_shares(self) -> None:
        """Clear the collected file shares."""
        self.file_shares = []

    # CollectorBase interface implementation
    def collect_data(self) -> list[dict]:
        """
        Start collecting Outlook file sharing data.

        This method starts the web server and waits for data from the Outlook add-in.

        Returns:
            List of file sharing data
        """
        # Start the server if not already running
        if not self.server_running:
            self.run_server()

        # For demonstration purposes, provide instructions to the user
        self.manifest_dir / "outlook-addin-manifest.xml"

        # In a real implementation, we would wait for data, but for now we'll return any existing data
        return self.get_file_shares()

    def process_data(self, data: Any) -> dict[str, Any]:
        """
        Process collected data.

        Args:
            data: Raw collected data

        Returns:
            Processed data
        """
        if isinstance(data, list):
            # Return the first file share if data is a list
            if data:
                return self.convert_to_email_file_share_model(data[0])
            return {}

        # Process a single file share
        if isinstance(data, dict):
            return self.convert_to_email_file_share_model(data)

        return {}

    def convert_to_email_file_share_model(self, file_share: dict) -> dict:
        """
        Convert a file share dict to an EmailFileShareData model.

        Args:
            file_share: Raw file share data

        Returns:
            EmailFileShareData as a dictionary
        """
        # Create the shared file data
        shared_file = SharedFileData(
            filename=file_share.get("filename", "Unknown"),
            url=file_share.get("url", ""),
            size_bytes=file_share.get("size"),
            content_type=file_share.get("content_type"),
            CollaborationType="outlook",
        )

        # Create the email file share model
        email_share = EmailFileShareData(
            EmailId=file_share.get("email_id", ""),
            Subject=file_share.get("subject", ""),
            Sender=file_share.get("sender", ""),
            Recipients=file_share.get("recipients", []),
            Timestamp=file_share.get(
                "timestamp",
                datetime.now(UTC).isoformat(),
            ),
            Files=[shared_file],
            FileShareType=file_share.get("attachment_type", "attachment"),
            CollaborationType="outlook",
        )

        return email_share.model_dump()

    def get_collector_characteristics(self) -> list[ActivityDataCharacteristics]:
        """Get the characteristics of the collector."""
        return [
            ActivityDataCharacteristics.ACTIVITY_DATA_FILE_SHARE,
            ActivityDataCharacteristics.ACTIVITY_DATA_COLLABORATION,
            ActivityDataCharacteristics.PROVIDER_COLLABORATION_DATA,
        ]

    def get_collectorr_name(self) -> str:
        """Get the name of the collector."""
        return self._name

    def get_provider_id(self) -> uuid.UUID:
        """Get the ID of the collector."""
        return self._provider_id

    def retrieve_data(self, data_id: str) -> dict:
        """
        Retrieve specific data by ID.

        Args:
            data_id: The ID of the data to retrieve

        Returns:
            The requested data
        """
        # In this simple implementation, just return an empty dict
        return {}

    def retrieve_temporal_data(
        self,
        reference_time: datetime,
        prior_time_window: timedelta,
        subsequent_time_window: timedelta,
        max_entries: int = 0,
    ) -> list[dict]:
        """
        Retrieve data within a time window.

        Args:
            reference_time: The reference time
            prior_time_window: Time window before reference
            subsequent_time_window: Time window after reference
            max_entries: Maximum number of entries to return

        Returns:
            List of data within the time window
        """
        start_time = reference_time - prior_time_window
        end_time = reference_time + subsequent_time_window

        # Filter file shares by timestamp
        result = []
        for file_share in self.file_shares:
            try:
                timestamp = datetime.fromisoformat(file_share.get("timestamp", ""))
                if start_time <= timestamp <= end_time:
                    result.append(file_share)
            except (ValueError, TypeError):
                continue

        # Apply limit if specified
        if max_entries > 0 and len(result) > max_entries:
            result = result[:max_entries]

        return result

    def get_cursor(self, activity_context: uuid.UUID) -> uuid.UUID:
        """
        Get a cursor for the activity context.

        Args:
            activity_context: The activity context

        Returns:
            A cursor UUID
        """
        # Generate a random UUID as a cursor
        return uuid.uuid4()

    def cache_duration(self) -> timedelta:
        """
        Get the cache duration for data.

        Returns:
            The cache duration
        """
        return timedelta(minutes=60)

    def get_description(self) -> str:
        """
        Get the description of the collector.

        Returns:
            The collector description
        """
        return self._description

    def get_json_schema(self) -> dict:
        """
        Get the JSON schema for the data.

        Returns:
            The JSON schema
        """
        return EmailFileShareData.model_json_schema()


def main() -> None:
    """Main function for testing the collector."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    try:
        # Create the collector
        collector = OutlookFileShareCollector(port=5000)

        # Start collecting data
        collector.collect_data()

        # For demonstration, let's simulate some file share data
        sample_data = {
            "emailId": "AAMkADRmMDExYzA3LThhYzgtNDRlOS1iMmJmLWNkYWM0ZjQ2ZmFkZQBGAAAAAADJRNbJqN3oQqtchVY9fVDoBwDtROOF92eoRKmzSJJuTTKdAAAAAAEJAADtROOF92eoRKmzSJJuTTKdAAFvmujTAAA=",
            "subject": "Sample file sharing email",
            "senderEmailAddress": "sender@example.com",
            "recipientEmailAddresses": [
                "recipient1@example.com",
                "recipient2@example.com",
            ],
            "timestamp": datetime.now(UTC).isoformat(),
            "attachments": [
                {
                    "fileName": "document.docx",
                    "attachmentType": "regular",
                    "contentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "size": 12345,
                    "id": "AAMkADRmMDExYzA3LThhYzgtNDRlOS1iMmJmLWNkYWM0ZjQ2ZmFkZQBGAAAAAADJRNbJqN3oQqtchVY9fVDoBwDtROOF92eoRKmzSJJuTTKdAAAAAAEJAADtROOF92eoRKmzSJJuTTKdAAFvmujTAAABEgAQAJ9cMJD03UZAi9/kR2Xcioo=",
                },
                {
                    "fileName": "spreadsheet.xlsx",
                    "attachmentType": "onedrive",
                    "url": "https://1drv.ms/x/s!AkP8HPJpsdfW98765gKJYT",
                },
            ],
        }

        # Process the sample data
        collector.process_email_data(sample_data)

        # Get and print the collected data
        file_shares = collector.get_file_shares()
        for _i, _file_share in enumerate(file_shares):
            pass

        # Process and print a model
        if file_shares:
            collector.process_data(file_shares[0])

        # Keep server running
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        collector.stop_server()

    except Exception as e:
        logging.exception(f"Error in main: {e}")

        # Try to clean up
        with contextlib.suppress(builtins.BaseException):
            collector.stop_server()


if __name__ == "__main__":
    main()
