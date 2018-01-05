# Item Catalog

## About
Item Catalog an application that provides a list of items within a variety of categories as well as provide a user registration and authentication system. Registered users will have the ability to post, edit and delete their own items. The application also provides the json endpoints.

## Tools required

Download and install all the following softwares:
* [VirtualBox](https://www.virtualbox.org/wiki/Download_Old_Builds_5_1)
* [Vagrant](https://www.vagrantup.com/)
* [Python](https://www.python.org/downloads/)
When all these tools are installed run these command in your terminal.
* To startup run **vagrant up**
* To log into Linux VM run **vagrant ssh**

## Setup
To setup you need to fork and clone this repository:
* [ fullstack-nanodegree-vm ](https://github.com/noshi1/fullstack-nanodegree-vm)

## Run
From your terminal cd to the folder where did you clone [fullstack-nanodegree-vm](https://github.com/noshi1/fullstack-nanodegree-vm) repository. Then access the shell with:

 * vagrant up

 * vagrant ssh

 * cd/vagrant/catalog

Then run the application:

* python models.py

* python populate_db.py

* python application.py

After the last command you are able to browse the application at this URL:

http://localhost:8000/
