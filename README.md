# Lingua Tile API
[![Deploy to Google Cloud Run](https://github.com/zliel/Lingua-Tile-Backend/actions/workflows/cicd.yml/badge.svg)](https://github.com/zliel/Lingua-Tile-Backend/actions/workflows/cicd.yml)

A simple, easy to use API for creating flashcards. This API is designed for use with the [Lingua Tile Frontend](https://github.com/zliel/lingua-tile), but is flexible enough be used for any flashcard application.
It makes use of a Lesson/Deck structure, and can be used to create courses, or just individual decks.

## Table of Contents
* [Getting Started](#getting-started)
  * [Prerequisites](#prerequisites)
  * [Setting up MongoDB](#setting-up-mongodb)
  * [Installing](#installing)
* [API Documentation](#api-documentation)
* [Built With](#built-with)
* [Author](#author)
* [Acknowledgments](#acknowledgments)

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

* Python 3.7 or higher
* MongoDB
* A RapidAPI account and API key for the [Deep Translate API](https://rapidapi.com/gatzuma/api/deep-translate1)

### Setting up MongoDB

There are two options for setting up MongoDB for this project:

1. **Using Atlas:** You can set up a MongoDB cluster using [Atlas](https://www.mongodb.com/cloud/atlas), MongoDB's cloud-based database service. Follow the instructions on the Atlas website to create a cluster, and then connect to the cluster using the MongoDB Compass GUI or the `mongo` shell.

2. **Running locally:** You can also run MongoDB locally on your machine. Follow the instructions on the [MongoDB website](https://docs.mongodb.com/manual/installation/) to install and run MongoDB on your machine.

### Installing

1. Clone the repository: <br>
`git clone https://github.com/zliel/Lingua-Tile-Backend.git`

2. Navigate to the project directory: <br>
`cd translation-flashcard-api`

3. Install the required packages: <br>
`pip install -r requirements.txt`

4. Set up the `.env` file: <br>
`cp .env.example .env`

5. Edit the `.env` file and replace the `MONGO_HOST` variable with the connection string for your MongoDB cluster or local instance. Also, add your RapidAPI API key to the `API_KEY` variable. You can obtain an API key by signing up for a RapidAPI account and subscribing to the Deep Translate API.

6. Run the application: <br>
`uvicorn main:app --reload`

### API Documentation

The API documentation is available at the `/docs` endpoint.

## Built With

* [FastAPI](https://fastapi.tiangolo.com/) - The web framework used
* [Pydantic](https://pydantic-docs.helpmanual.io/) - Used for data validation and modeling
* [PyMongo](https://pymongo.readthedocs.io/) - Used for interacting with MongoDB

## Author

* **Zliel** - *Creator* - [My Profile](https://github.com/zliel)

## Acknowledgments

* Special thanks to MongoDB for their [article](https://www.mongodb.com/developer/languages/python/python-quickstart-fastapi/) on using FastAPI and PyMongo, which helped me to change the python classes into Pydantic models.
