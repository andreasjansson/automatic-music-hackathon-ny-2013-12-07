import collections
import random
import time
import alsaseq
import alsamidi
import curses
import curses.wrapper
import signal
import sys


SLEEP_TIME = 0.2

MEMORY_LENGTH = 4
INTRODUCTION_LENGTH = 2
MAX_PARTS = 6

MIN_PITCH = 50
MAX_PITCH = 90
MAX_JUMP = 2
NOTE_PROB = .2
MIN_LENGTH = 3
MAX_LENGTH = 30
KICK = 36
SNARE = 38
HIHAT = 50

NOTE_NAMES = ['c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#', 'a', 'a#', 'b']

# instruments:
# 01 013 Marimba
# 02 009 Celesta
# 03 067 TenorSax
# 04 012 Vibes
# 05 057 Trumpet
# 06 006 E.Piano2
# 07 011 MusicBox

play_while_training = True

def main(screen):

    curses.use_default_colors()
    for i in range(0, curses.COLORS):
        curses.init_pair(i, i, -1)

    done = False
    time_without_change = 0
    iterations = 0

    parts = []
    memory = collections.deque(maxlen=MEMORY_LENGTH)
    while True:
        iterations += 1

        if len(parts) == 0:
            parts.append(Part(0))

        elif all([part.n_iterations >= INTRODUCTION_LENGTH for part in parts]):
            if len(parts) == MAX_PARTS:
                done = True
            else:
                part = new_consonant_part(len(parts), memory)
                parts.append(Part(len(parts)))
            
        notes = []
        for i, part in enumerate(parts):
            note = part.head()

            display_part(screen, part, False)

            if note is not None:
                if is_dissonant(note, memory):
                    display_part(screen, part, True)
                    time_without_change = 0
                    parts[i] = new_consonant_part(i, memory)
                    continue
                else:
                    notes.append(note)

            part.rotate()

        if play_while_training or (done and time_without_change > 100):
            if notes:
                midi_play(notes)
            else:
                time.sleep(SLEEP_TIME)
        else:
            iterations += 1

        time_without_change += 1

        memory += notes

def display_part(screen, part, has_changed=False):
    s = []
    for note in part.notes:
        if note:
            s.append('%3s' % get_note_name(note.pitch))
        else:
            s.append(' - ')
    s.append(' ' * ((MAX_LENGTH - len(s)) * 4))
    if has_changed:
        screen.addstr(1 + part.channel, 1, s[0], curses.color_pair(3))
        screen.addstr(1 + part.channel, 5, ' '.join(s[1:]), curses.color_pair(1))
    else:
        screen.addstr(1 + part.channel, 1, s[0], curses.color_pair(3))
        screen.addstr(1 + part.channel, 5, ' '.join(s[1:]), curses.color_pair(0))
    screen.refresh()

def get_note_name(pitch):
    pitch_class = pitch % 12
    octave = (pitch - 12) // 12
    return '%s%d' % (NOTE_NAMES[pitch_class], octave)

def new_consonant_part(channel, memory):
    for _ in range(100):
        part = Part(channel)
        for note in part.notes:
            if note and is_dissonant(note, memory):
                break
        else:
            return part
    return part
    

def is_dissonant(note, memory):
    pitches = [False] * 5
    pitches[2] = True
    for memory_note in memory:
        if memory_note and abs((note.pitch % 12) - (memory_note.pitch % 12)) <= 2:
            pitches[(memory_note.pitch % 12) - (note.pitch % 12)] = True

    # fuck science
    return ((pitches[0] and pitches[1] and pitches[2]) or
            (pitches[1] and pitches[2] and pitches[3]) or
            (pitches[2] and pitches[3] and pitches[4]))

alsaseq.client('arp', 1, 1, False)
alsaseq.connectto(1, 20, 0)

def sigint_handler(signal, frame):
    finish()
    sys.exit(1)

def finish():
    curses.nocbreak()
    curses.echo()
    curses.endwin()
    print 'cleaning up'
    for channel in range(16):
        for pitch in range(128):
            alsaseq.output(alsamidi.noteoffevent(channel, pitch, 0))

signal.signal(signal.SIGINT, sigint_handler)

def midi_play(notes):
    for note in notes:
        alsaseq.output(alsamidi.noteonevent(note.channel, note.pitch, 100))
    time.sleep(SLEEP_TIME)
    for note in notes:
        alsaseq.output(alsamidi.noteoffevent(note.channel, note.pitch, 0))

class Part(object):

    def __init__(self, channel):
        self.channel = channel
        self.notes = self.generate_notes()
        self.n_iterations = 0
        self.rotation = 0

    def generate_notes(self):
        root = random.randint(MIN_PITCH, MAX_PITCH)
        scale = [root, root + 2, root + 4, root + 9]
        length = random.randint(MIN_LENGTH, MAX_LENGTH)

        indices = [None] * length
        first_index = random.randint(0, len(scale) - 1)
        indices[0] = first_index
        prev_index = first_index
        for i in xrange(1, length):
            if random.random() < NOTE_PROB:
                indices[i] = random.randint(0, 3)
                continue

                jump = random.randint(-MAX_JUMP, MAX_JUMP)
                index = prev_index + jump
                if index >= len(scale) or index < 0:
                    jump = -jump

                index = prev_index + jump
                if index < 0:
                    index = 0
                elif index >= len(scale):
                    index = len(scale) - 1
                indices[i] = index
                prev_index = index

        notes = collections.deque([None] * length)
        for i, index in enumerate(indices):
            if index is not None:
                notes[i] = Note(scale[index], self.channel)

        notes.rotate(random.randint(0, len(notes)))

        return notes

    def rotate(self):
        self.notes.rotate(-1)
        self.rotation += 1
        if self.rotation == len(self.notes):
            self.rotation = 0
            self.n_iterations += 1

    def head(self):
        return self.notes[0]

class Note(object):
    def __init__(self, pitch, channel):
        self.pitch = pitch
        self.channel = channel

if __name__ == '__main__':
    curses.wrapper(main)
