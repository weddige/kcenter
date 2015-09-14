#!/bin/bash

PYTHON=~konstantin/.virtualenvs/masterarbeit/bin/python
KAPIDIR=~konstantin/Dokumente/Masterarbeit/src/
PIDFILE=/tmp/kapi.pid
PORT=8887

start() {
    echo -n "Start KAPI: "
    if [ -f $PIDFILE ]; then
        PID=`cat $PIDFILE`
        echo "already running: $PID"
        exit 2;
    else
        cd $KAPIDIR
        PID=`$PYTHON ./kapi.py -p $PORT > /dev/null 2>&1 & echo $!`
        if [ -z $PID ]; then
            echo "Failed"
        else
            echo $PID > $PIDFILE
            echo "OK"
        fi
    fi
}

stop() {
    echo -n "Stop KAPI: "

    if [ -f $PIDFILE ]; then
        PID=`cat $PIDFILE`
        kill $PID
        rm $PIDFILE
        echo "stoped"
    else
        echo "no pidfile found"
    fi
}

status() {
    echo -n "KAPI is "

	if [ -f $PIDFILE ]; then
        PID=`cat $PIDFILE`
        if ps -p $PID > /dev/null; then
            echo "running"
        else
            echo "not running but pidfile exists"
        fi
    else
        echo "not running"
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        start
        ;;
    status)
        status python
        ;;
    *)
        echo "Usage: {start|stop|restart|status}"
        exit 1
        ;;
esac
exit $?
