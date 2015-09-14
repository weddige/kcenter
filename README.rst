K-CENTER API
============
Installation
------------

.. code-block::

   sudo apt-get install python-virtualenev
   sudo apt-get install python3

   mkvirtualenv -p /usr/bin/python3 kcenter
   workon kcenter

   sudo apt-get build-dep python3-lxml
   sudo apt-get build-dep python3-numpy python3-scipy python3-matplotlib ipython3 ipython3-notebook
   sudo apt-get build-dep python3-pandas python3-nose

   pip install -r requirements.txt

Run the Server
--------------

.. code-block::

   usage: kapi.py [-h] [--logging {DEBUG,INFO,WARNING,ERROR}] [-c] [-p PORT]

   optional arguments:
     -h, --help            show this help message and exit
     --logging {DEBUG,INFO,WARNING,ERROR}
                           Set log level
     -c, --cython          Compile algorithms with cython
     -p PORT, --port PORT  Set port

The server does not daemonize itself but kapi.sh allows to run it in the background:

.. code-block::

   Usage: {start|stop|restart|status}

But first you have to adjust both PYTHON and KAPIDIR in line 3 and 4 according to your local setup.