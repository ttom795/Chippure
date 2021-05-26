'''
Chippure by Toby Tomkinson

Copyright (c) 2021, Toby Tomkinson
All rights reserved.

TODO:
Sound toggle
Speed adjustment
Emulator pause
Save/Load state system
Scaling option/slider
'''

import tkinter
import math
import time
import random
import sys

class Renderer:
    def __init__(self, scale):
        self.window = tkinter.Tk()
        self.window.title("Chippure by Toby T.")
        self.scale = scale
        self.cols = 64
        self.rows = 32
        self.window.attributes("-topmost", True)
        self.canvas = tkinter.Canvas(self.window, width=self.cols*scale, height=self.rows*scale, bg='Black')
        self.canvas.pack()
        self.display = [0 for i in range(2048)]

    def clearDisplay(self):
        self.canvas.delete('all')

    def clear(self):
        self.display = [0 for i in range(2048)]

    def setPixel(self,x,y):
        if x > self.cols -1:
            while x > self.cols-1:
                x -= self.cols
        if x < 0:
            while x < 0:
                x += self.cols
        if y > self.rows-1:
            while y > self.rows-1:
                y -= self.rows
        if y < 0:
            while y < 0:
                y += self.rows
        pixelPos = x+(y*self.cols)
        self.display[pixelPos] = self.display[pixelPos] ^ 1
        return not self.display[pixelPos]

    def render(self):
        self.clearDisplay()
        for i in range(self.cols*self.rows):
            x = (i%self.cols) * self.scale
            y = math.floor(i/self.cols) * self.scale
            if self.display[i] == 1:
                self.canvas.create_rectangle(2+x,2+y,2+self.scale+x,2+self.scale+y,fill="white",width=0)

class Keyboard:
    def __init__(self, screen):
        self.current_keys = []
        self.recent_key = None
        for i in range(16):
            self.current_keys.append(False)
        self.keys = ['1','2','3','4',
                     'q','w','e','r',
                     'a','s','d','f',
                     'z','x','c','v']
        self.hex = [0x1,0x2,0x3,0xc,
                    0x4,0x5,0x6,0xD,
                    0x7,0x8,0x9,0xE,
                    0xA,0x0,0xB,0xF]
        self.screen = screen
        self.screen.window.bind('<Key>',self.inputEventDown)
        self.screen.window.bind('<KeyRelease>',self.inputEventUp)

    def inputEventDown(self, event):
        if event.keysym == "Escape":
            quit()
        if event.char in self.keys:
            index = self.keys.index(event.char) #look in list, get index
            self.recent_key = self.hex[index]

    def inputEventUp(self, event):
        if event.char in self.keys and self.recent_key != None:
            index = self.hex.index(self.recent_key)
            key_string = self.keys[index]
            if event.char == key_string:
                self.recent_key = None

    def isKeyPressed(self,code):
        return self.recent_key == code

class CPU:
    def __init__(self, renderer, keyboard):
        self.renderer = renderer
        self.keyboard = keyboard
        self.memory = [0x0 for i in range(4096)]
        self.v = [0x0 for i in range(16)]
        self.i = 0
        self.pc = 0x200
        self.stack = []
        self.delayTimer = 0
        self.soundTimer = 0
        self.paused = False
        self.speed = 15

        self.memory[:80] = [
        0xF0, 0x90, 0x90, 0x90, 0xF0,
        0x20, 0x60, 0x20, 0x20, 0x70,
        0xF0, 0x10, 0xF0, 0x80, 0xF0,
        0xF0, 0x10, 0xF0, 0x10, 0xF0,
        0x90, 0x90, 0xF0, 0x10, 0x10,
        0xF0, 0x80, 0xF0, 0x10, 0xF0,
        0xF0, 0x80, 0xF0, 0x90, 0xF0,
        0xF0, 0x10, 0x20, 0x40, 0x40,
        0xF0, 0x90, 0xF0, 0x90, 0xF0,
        0xF0, 0x90, 0xF0, 0x10, 0xF0,
        0xF0, 0x90, 0xF0, 0x90, 0x90,
        0xE0, 0x90, 0xE0, 0x90, 0xE0,
        0xF0, 0x80, 0x80, 0x80, 0xF0,
        0xE0, 0x90, 0x90, 0x90, 0xE0,
        0xF0, 0x80, 0xF0, 0x80, 0xF0,
        0xF0, 0x80, 0xF0, 0x80, 0x80
        ]

    def loadRom(self, romName):
        data = []
        with open(romName, 'rb') as f:
            program = f.read()
            for i in program:
                data.append(i)
        offset = int('0x200',16)
        for i in range(len(program)):
            self.memory[offset+i] = program[i]

    def cycle(self):
        for i in range(self.speed):
            if self.paused == False:
                opcode = self.memory[self.pc] << 8 | self.memory[self.pc+1]
                self.executeInstruction(opcode)
        if self.paused == False:
            self.updateTimers()
        self.beep()
        self.renderer.render()
        self.renderer.window.update()

    def beep(self):
        if self.soundTimer > 0:
            try:
                import winsound
                winsound.Beep(440,100) #freq, ms
            except:
                sys.stdout.write('\a')

    def updateTimers(self):
        self.delayTimer -= int(self.delayTimer > 0)
        self.soundTimer -= int(self.soundTimer > 0)

    def executeInstruction(self,opcode):
        self.pc += 2

        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        code = (opcode & 0xF000)
        kk = (opcode & 0xFF)

        if code == 0x0000:
            if opcode == 0x00E0: #CLS
                self.renderer.clear()

            elif opcode == 0x00EE: #RET
                self.pc = self.stack.pop()

        elif code == 0x1000: #JP addr
            self.pc = (opcode & 0xFFF)

        elif code == 0x2000: #CALL addr
            self.stack.append(self.pc)
            self.pc = (opcode & 0xFFF)

        elif code == 0x3000: #SE Vx, byte
            if self.v[x] == kk:
                self.pc += 2

        elif code == 0x4000: #SNE Vx, byte
            if self.v[x] != kk:
                self.pc += 2

        elif code == 0x5000: #SE Vx, Vy
            if self.v[x] == self.v[y]:
                self.pc += 2

        elif code == 0x6000: #LD Vx, byte
            self.v[x] = kk

        elif code == 0x7000: #ADD Vx, byte
            self.v[x] = (self.v[x]+kk)&0xFF

        elif code == 0x8000:
            if (opcode & 0xF) == 0x0: #LD Vx, Vy
                self.v[x] = self.v[y]

            elif (opcode & 0xF) == 0x1: #OR Vx, Vy
                self.v[x] |= self.v[y]

            elif (opcode & 0xF) == 0x2: #AND Vx, Vy
                self.v[x] &= self.v[y]

            elif (opcode & 0xF) == 0x3: #XOR Vx, Vy
                self.v[x] ^= self.v[y]

            elif (opcode & 0xF) == 0x4: #ADD Vx, Vy
                tempSum = self.v[x] + self.v[y]
                self.v[0xF] = int(tempSum > 0xFF)
                self.v[x] = tempSum & 0xFF

            elif (opcode & 0xF) == 0x5: #SUB Vx, Vy
                self.v[0xF] = int(self.v[x] > self.v[y])
                self.v[x] = (self.v[x]-self.v[y])&0xFF

            elif (opcode & 0xF) == 0x6: #SHR Vx {, Vy}
                temp = self.v[x] & 0x1
                self.v[x] = (self.v[x] >> 1)&0xFF
                self.v[0xF] = temp

            elif (opcode & 0xF) == 0x7: #SUBN Vx, Vy
                self.v[0xF] = int(self.v[y] > self.v[x])
                self.v[x] = (self.v[y]-self.v[x])&0xFF

            elif (opcode & 0xF) == 0xE: #SHL Vx {, Vy}
                temp = (self.v[x]%0x80)>>7
                self.v[x] = (self.v[x]<<0x1)&0xFF
                self.v[0xF] = temp

        elif code == 0x9000: #SNE Vx, Vy
            if self.v[x] != self.v[y]:
                self.pc += 2

        elif code == 0xA000: #LD I, addr
            self.i = opcode & 0xFFF

        elif code == 0xB000: #JP V0, addr
            self.pc = (opcode & 0xFFF) + self.v[0]

        elif code == 0xC000: #RND Vx, byte
            rand = math.floor(random.random() * 0xFF)
            self.v[x] = rand & kk

        elif code == 0xD000: #DRW Vx, Vy, nibble
            width = 8
            height = opcode & 0x000F
            self.v[0xF] = 0
            for row in range(height):
                sprite = self.memory[self.i+row]
                for col in range(width):
                    if ((sprite & 0x80) > 0):
                        if self.renderer.setPixel(self.v[x]+col, self.v[y]+row):
                            self.v[0xF] = 1
                    sprite = sprite << 1

        elif code == 0xE000:
            key = self.v[x]
            if kk == 0x9E: #SKP Vx
                if self.keyboard.recent_key == key:
                    self.pc += 2

            elif kk == 0xA1: #SKNP Vx
                if not self.keyboard.recent_key == key:
                    self.pc += 2

        elif code == 0xF000:
            if kk == 0x07: #LD Vx, DT
                self.v[x] = self.delayTimer

            elif kk == 0x0A: #LD Vx, K
                print("pause func.")
                self.paused = True  #tbh I have no idea if this function is working or not
                if self.keyboard.recent_key == None:
                    time.sleep(0.5)
                    self.executeInstruction(opcode)
                self.v[x] = self.keyboard.recent_key
                print(self.v[x])
                self.paused = False

            elif kk == 0x15: #LD DT, Vx
                self.delayTimer = self.v[x]

            elif kk == 0x18: #LD ST, Vx
                self.soundTimer = self.v[x]

            elif kk == 0x1E: #ADD I, Vx
                self.i += self.v[x]

            elif kk == 0x29: #LD F, Vx
                self.i = self.v[x]*0x5

            elif kk == 0x33: #LD B, Vx
                self.memory[self.i] = int(self.v[x] / 100)
                self.memory[self.i + 1] = int((self.v[x] % 100) / 10)
                self.memory[self.i + 2] = int(self.v[x] % 10)

            elif kk == 0x55: #LD [I], Vx
                for registerIndex in range(x+1):
                    self.memory[self.i+registerIndex] = self.v[registerIndex]

            elif kk == 0x65: #LD Vx, [I]
                for registerIndex in range(x+1):
                    self.v[registerIndex] = self.memory[self.i+registerIndex]
        else:
            print("unknown opcode: "+opcode)

def main():
    romName = input("Enter rom: ")
    screen = Renderer(6)            #Screen scale as a multiple of 128*64
    FPS = 60
    keyboard = Keyboard(screen)
    cpu = CPU(screen, keyboard)
    cpu.loadRom(romName)
    while True:
        time.sleep(1/FPS)
        cpu.cycle()
main()
