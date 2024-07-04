'''
Project Indaleko
Copyright (C) 2024 Tony Mason

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
'''
import argparse
from icecream import ic

apollo_dockerfile_template = \
'''
# Use the official Node.js image.
FROM node:14

# Create and change to the app directory.
WORKDIR /usr/src/app

# Install app dependencies.
COPY package*.json ./
RUN npm install

# Copy app source code.
COPY . .

# Expose the port Apollo Server will run on.
EXPOSE 4000

# Start the Apollo Server.
CMD ["node", "index.js"]
'''

def main():
    parse = argparse.ArgumentParser(description='Apollo setup')
    parse.add_argument('--setup', help='Setup Apollo')
    parse.add_argument('--run', help='Run Apollo')
    args = parse.parse_args()
    print(args)


if __name__ == '__main__':
    main()
