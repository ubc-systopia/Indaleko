from flask import Flask, render_template, request
import configparser
import subprocess

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("getting_started.html")


@app.route("/configure", methods=["GET", "POST"])
def configure():
    if request.method == "POST":
        if "local_setup" in request.form:
            # Run the local setup script
            setup_local_arango()
            return "Local ArangoDB instance set up successfully!"

        elif "remote_setup" in request.form:
            # Capture form data for remote setup
            database = request.form.get("database")
            host = request.form.get("host")
            port = request.form.get("port")
            admin_user = request.form.get("admin_user")
            admin_passwd = request.form.get("admin_passwd")

            # Write to an INI file
            config = configparser.ConfigParser()
            config["database"] = {
                "database": database,
                "host": host,
                "port": port,
                "admin_user": admin_user,
                "admin_passwd": admin_passwd,
            }
            with open("arangodb_config.ini", "w") as configfile:
                config.write(configfile)

            return "Remote configuration saved successfully!"

    return render_template("configure.html")


def setup_local_arango():
    try:
        subprocess.run(["bash", "./setup_arangodb.sh"], check=True)
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"Failed to set up local ArangoDB instance: {e}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
