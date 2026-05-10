#!/bin/bash -x

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

tmux new-session -d -s supervisord "/root/.local/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf"
tmux new-session -d -s video "/usr/bin/python3 /root/zmq_videopub.py ; sleep inf"

# Wait for the serial port to be available
while [ ! -e /dev/ttyAMA0 ]; do
    sleep 1
done

tmux new-session -d -s data "python3 /root/DOGZILLAProxyServer.py ; sleep inf"

# Wait for UDP port 5002 to start listening
while ! netstat -tuln | grep -q ":5002 "; do
    sleep 1
done
tmux new-session -d -s webvideo "cd /root && source .flask/bin/activate && python3 web_video.py ; sleep inf"
#tmux new-session -d -s webjoy "cd /root && source .flask/bin/activate && python3 web_joy.py ; sleep inf"
#tmux new-session -d -s webjoy "cd /root && source .yolo/bin/activate && python3 web_joy.py ; sleep inf"
#tmux new-session -d -s webvoice "cd /root && source .flask/bin/activate && python3 web_voice.py ; sleep inf"
#tmux new-session -d -s webvoice "cd /root && source .yolo/bin/activate && python3 web_voice.py ; sleep inf"
#tmux new-session -d -s webmutasd "cd /root && source .flask/bin/activate && python3 web_mutasd.py ; sleep inf"
tmux new-session -d -s webmain "cd /root && source .flask/bin/activate && python3 web_main.py ; sleep inf"

# Legacy standalone behavior stays available by default.
MODE="${MODE:-}"
if [ "${MODE}" = "fsm" ]; then
    tmux new-session -d -s fsm "cd /root && source .yolo/bin/activate && python3 state_machine.py ; sleep inf"
    tmux new-session -d -s webfsm "cd /root && source .flask/bin/activate && python3 web_fsm.py ; sleep inf"
elif [ "${MODE}" = "keresd" ]; then
    tmux new-session -d -s detect "cd /root && source .yolo/bin/activate && python3 keresd.py ; sleep inf"
    tmux new-session -d -s webkeresd "cd /root && source .flask/bin/activate && python3 web_keresd.py ; sleep inf"

elif [ "${MODE}" = "kovesd" ]; then
    tmux new-session -d -s follow "cd /root && source .yolo/bin/activate && python3 kovesd.py ; sleep inf"
    tmux new-session -d -s webkovesd "cd /root && source .flask/bin/activate && python3 web_kovesd.py ; sleep inf"
else
    tmux new-session -d -s detect "cd /root && source .yolo/bin/activate && python3 keresd.py ; sleep inf"
    tmux new-session -d -s webkeresd "cd /root && source .flask/bin/activate && python3 web_keresd.py ; sleep inf"
    tmux new-session -d -s follow "cd /root && source .yolo/bin/activate && python3 kovesd.py ; sleep inf"
    tmux new-session -d -s webkovesd "cd /root && source .flask/bin/activate && python3 web_kovesd.py ; sleep inf"
fi

tail -f /dev/null