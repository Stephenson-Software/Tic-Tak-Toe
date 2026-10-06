import asyncio
import sys
import time

import pygame
import random
from Graphik import Graphik


def runningInBrowser():
    # pygbag runs the game under CPython compiled to WebAssembly
    return sys.platform == "emscripten"


def ignoreHeldButton():
    # Graphik.drawButton calls its function on every frame the left button is held over the
    # box, and it cannot await the game's handlers; a button is pressed from the press event
    # in TicTacToe.endFrame instead
    pass


def pressLandedOn(pressPos, xpos, ypos, width, height):
    # the same bounds Graphik.drawButton uses for the cursor
    return pressPos is not None and xpos + width > pressPos[0] > xpos and ypos + height > pressPos[1] > ypos


#  @author Daniel McCoy Stephenson
#  @since August 6th, 2022
class TicTacToe:
    framesPerSecond = 60

    def __init__(self):
        if runningInBrowser():
            # every page load would otherwise start from the same random state, so each
            # visitor would face the same sequence of computer moves
            random.seed(time.time_ns())

        pygame.init()

        self.black = (0,0,0)
        self.white = (255,255,255)

        self.displayWidth = 800
        self.displayHeight = 600

        self.gameDisplay = pygame.display.set_mode((self.displayWidth, self.displayHeight))

        self.graphik = Graphik(self.gameDisplay)

        pygame.display.set_caption("Tic Tac Toe")

        self.clock = pygame.time.Clock()

        self.topLeftL = ""
        self.topMiddleL = ""
        self.topRightL = ""

        self.middleLeftL = ""
        self.middleMiddleL = ""
        self.middleRightL = ""

        self.bottomLeftL = ""
        self.bottomMiddleL = ""
        self.bottomRightL = ""

        self.moves = 0

        # the buttons drawn in the current frame, as (xpos, ypos, width, height, text, function)
        self.buttons = []

    def drawGridSlot(self, xpos, ypos, XorO, function):
        self.drawButton(xpos, ypos, 100, 100, self.white, self.black, 64, XorO, function)

    def drawButton(self, xpos, ypos, width, height, colorBox, colorText, sizeText, text, function):
        # Graphik draws the button; the button is remembered so that a press landing on it in
        # this frame awaits its function once the frame is drawn
        self.graphik.drawButton(xpos, ypos, width, height, colorBox, colorText, sizeText, text, ignoreHeldButton)
        self.buttons.append((xpos, ypos, width, height, text, function))

    def drawQuitButton(self, xpos, ypos, width, height, sizeText):
        # A browser tab has nothing to quit to (closing the tab is how a visitor leaves), so the
        # browser build offers no Quit button
        if not runningInBrowser():
            self.drawButton(xpos, ypos, width, height, self.black, self.white, sizeText, "Quit", self.exit)

    def readEvents(self):
        # Returns where a left-button press landed during this frame, or None. A press and
        # release landing in the same frame (how a browser tap arrives) still counts, and a
        # button held down presses nothing further.
        pressPos = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pressPos = event.pos
        return pressPos

    def discardPressesMadeDuringThePause(self):
        # The end screens open after a one-second pause, during which the board is still shown;
        # a tap made then was aimed at the board, and must not press the button that is drawn
        # where it landed (Play Again covers the bottom-middle cell)
        pygame.event.clear((pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP))

    def beginFrame(self):
        self.buttons = []
        self.gameDisplay.fill(self.white)

    async def endFrame(self, pressPos):
        pygame.display.update()
        self.clock.tick(self.framesPerSecond)
        # hands control back to the browser once per frame; a no-op pause on the desktop
        await asyncio.sleep(0)
        await self.pressButton(pressPos)

    async def pressButton(self, pressPos):
        for xpos, ypos, width, height, text, function in list(self.buttons):
            if pressLandedOn(pressPos, xpos, ypos, width, height):
                await function()
                return

    async def exit(self):
        pygame.quit()
        quit()

    async def topLeft(self):
        if self.topLeftL == "":
            self.topLeftL = "X"
            self.drawGrid()
            self.moves += 1
            await self.computerTurn()

    async def topMiddle(self):
        if self.topMiddleL == "":
            self.topMiddleL = "X"
            self.drawGrid()
            self.moves += 1
            await self.computerTurn()

    async def topRight(self):
        if self.topRightL == "":
            self.topRightL = "X"
            self.drawGrid()
            self.moves += 1
            await self.computerTurn()

    async def middleLeft(self):
        if self.middleLeftL == "":
            self.middleLeftL = "X"
            self.drawGrid()
            self.moves += 1
            await self.computerTurn()

    async def middleMiddle(self):
        if self.middleMiddleL == "":
            self.middleMiddleL = "X"
            self.drawGrid()
            self.moves += 1
            await self.computerTurn()

    async def middleRight(self):
        if self.middleRightL == "":
            self.middleRightL = "X"
            self.drawGrid()
            self.moves += 1
            await self.computerTurn()

    async def bottomLeft(self):
        if self.bottomLeftL == "":
            self.bottomLeftL = "X"
            self.drawGrid()
            self.moves += 1
            await self.computerTurn()    

    async def bottomMiddle(self):
        if self.bottomMiddleL == "":
            self.bottomMiddleL = "X"
            self.drawGrid()
            self.moves += 1
            await self.computerTurn()  

    async def bottomRight(self):
        if self.bottomRightL == "":
            self.bottomRightL = "X"
            self.drawGrid()
            self.moves += 1
            await self.computerTurn()  

    async def computerTurn(self):
        await self.checkForWinCondition()
        
        if self.moves != 9:
            await asyncio.sleep(1)

            went = False
            while (went == False):
                randomInt = random.randint(1,10)
                if randomInt == 1:
                    if self.topLeftL == "":
                        self.topLeftL = "O"
                        went = True
                        self.moves += 1
                if randomInt == 2:
                    if self.topMiddleL == "":
                        self.topMiddleL = "O"
                        went = True
                        self.moves += 1
                if randomInt == 3:
                    if self.topRightL == "":
                        self.topRightL = "O"
                        went = True
                        self.moves += 1
                if randomInt == 4:
                    if self.middleLeftL == "":
                        self.middleLeftL = "O"
                        went = True
                        self.moves += 1
                if randomInt == 5:
                    if self.middleMiddleL == "":
                        self.middleMiddleL = "O"
                        went = True
                        self.moves += 1
                if randomInt == 6:
                    if self.middleRightL == "":
                        self.middleRightL = "O"
                        went = True
                        self.moves += 1
                if randomInt == 7:
                    if self.bottomLeftL == "":
                        self.bottomLeftL = "O"
                        went = True
                        self.moves += 1
                if randomInt == 8:
                    if self.bottomMiddleL == "":
                        self.bottomMiddleL = "O"
                        went = True
                        self.moves += 1
                if randomInt == 9:
                    if self.bottomRightL == "":
                        self.bottomRightL = "O"
                        went = True
                        self.moves += 1
        self.drawGrid()
        await self.checkForWinCondition()
        
    def drawGrid(self):
        centerGridX = (self.displayWidth//2 - 50)
        centerGridY = (self.displayHeight//2 - 50)
        
        self.graphik.drawRectangle(centerGridX - 125, centerGridY - 125, 350, 350, self.black)
        
        self.drawGridSlot(centerGridX - 125, centerGridY - 125, self.topLeftL, self.topLeft) # top row left column
        self.drawGridSlot(centerGridX, centerGridY - 125, self.topMiddleL, self.topMiddle) # top row middle column
        self.drawGridSlot(centerGridX + 125, centerGridY - 125, self.topRightL, self.topRight) # top row right column
        
        self.drawGridSlot(centerGridX - 125, centerGridY, self.middleLeftL, self.middleLeft) # middle row left column
        self.drawGridSlot(centerGridX, centerGridY, self.middleMiddleL, self.middleMiddle) # middle row middle column
        self.drawGridSlot(centerGridX + 125, centerGridY, self.middleRightL, self.middleRight) # middle row right column

        self.drawGridSlot(centerGridX - 125, centerGridY + 125, self.bottomLeftL, self.bottomLeft) # bottom row left column
        self.drawGridSlot(centerGridX, centerGridY + 125, self.bottomMiddleL, self.bottomMiddle) # bottom row middle column
        self.drawGridSlot(centerGridX + 125, centerGridY + 125, self.bottomRightL, self.bottomRight) # bottom row right column
        
        pygame.display.update()

    async def restart(self):
        self.topLeftL = ""
        self.topMiddleL = ""
        self.topRightL = ""

        self.middleLeftL = ""
        self.middleMiddleL = ""
        self.middleRightL = ""

        self.bottomLeftL = ""
        self.bottomMiddleL = ""
        self.bottomRightL = ""
        
        self.moves = 0
        await self.titleScreen()

    async def playerWin(self):
        await asyncio.sleep(1)
        self.discardPressesMadeDuringThePause()

        while self.moves > 0:
            pressPos = self.readEvents()

            self.beginFrame()
            self.graphik.drawText("You won!", self.displayWidth//2, self.displayHeight//4, 64, self.black)
            middleButtonXPos = self.displayWidth//2 - 50
            self.drawButton(middleButtonXPos, self.displayHeight - 200, 100, 50, self.black, self.white, 16, "Play Again", self.restart)
            self.drawQuitButton(middleButtonXPos, self.displayHeight - 100, 100, 50, 20)

            await self.endFrame(pressPos)
        
    async def computerWin(self):
        await asyncio.sleep(1)
        self.discardPressesMadeDuringThePause()

        while self.moves > 0:
            pressPos = self.readEvents()

            self.beginFrame()
            self.graphik.drawText("You lost!", self.displayWidth//2, self.displayHeight//4, 64, self.black)
            middleButtonXPos = self.displayWidth//2 - 50
            self.drawButton(middleButtonXPos, self.displayHeight - 200, 100, 50, self.black, self.white, 16, "Play Again", self.restart)
            self.drawQuitButton(middleButtonXPos, self.displayHeight - 100, 100, 50, 20)

            await self.endFrame(pressPos)
                
    async def tie(self):
        await asyncio.sleep(1)
        self.discardPressesMadeDuringThePause()

        while self.moves > 0:
            pressPos = self.readEvents()

            self.beginFrame()
            self.graphik.drawText("It's a tie!", self.displayWidth//2, self.displayHeight//4, 64, self.black)
            middleButtonXPos = self.displayWidth//2 - 50
            self.drawButton(middleButtonXPos, self.displayHeight - 200, 100, 50, self.black, self.white, 16, "Play Again", self.restart)
            self.drawQuitButton(middleButtonXPos, self.displayHeight - 100, 100, 50, 20)

            await self.endFrame(pressPos)

    async def checkForWinCondition(self):
        # case top row
        if self.topLeftL == "X" and self.topMiddleL == "X" and self.topRightL == "X":
            await self.playerWin()
            
        if self.topLeftL == "O" and self.topMiddleL == "O" and self.topRightL == "O":
            await self.computerWin()
        
        # case middle row
        if self.middleLeftL == "X" and self.middleMiddleL == "X" and self.middleRightL == "X":
            await self.playerWin()
            
        if self.middleLeftL == "O" and self.middleMiddleL == "O" and self.middleRightL == "O":
            await self.computerWin()
        
        # case bottom row
        if self.bottomLeftL == "X" and self.bottomMiddleL == "X" and self.bottomRightL == "X":
            await self.playerWin()
            
        if self.bottomLeftL == "O" and self.bottomMiddleL == "O" and self.bottomRightL == "O":
            await self.computerWin()
        
        # case left column
        if self.topLeftL == "X" and self.middleLeftL == "X" and self.bottomLeftL == "X":
            await self.playerWin()
            
        if self.topLeftL == "O" and self.middleLeftL == "O" and self.bottomLeftL == "O":
            await self.computerWin()
        
        # case middle column
        if self.topMiddleL == "X" and self.middleMiddleL == "X" and self.bottomMiddleL == "X":
            await self.playerWin()
            
        if self.topMiddleL == "O" and self.middleMiddleL == "O" and self.bottomMiddleL == "O":
            await self.computerWin()
        
        # case right column
        if self.topRightL == "X" and self.middleRightL == "X" and self.bottomRightL == "X":
            await self.playerWin()
            
        if self.topRightL == "O" and self.middleRightL == "O" and self.bottomRightL == "O":
            await self.computerWin()
        
        # case diagonal ->
        if self.topLeftL == "X" and self.middleMiddleL == "X" and self.bottomRightL == "X":
            await self.playerWin()
            
        if self.topLeftL == "O" and self.middleMiddleL == "O" and self.bottomRightL == "O":
            await self.computerWin()
            
        # case diagonal <-
        if self.topRightL == "X" and self.middleMiddleL == "X" and self.bottomLeftL == "X":
            await self.playerWin()
            
        if self.topRightL == "O" and self.middleMiddleL == "O" and self.bottomLeftL == "O":
            await self.computerWin()
            
        if self.moves == 9:
            await self.tie()

    async def gridScreen(self):
        running = True

        while running:
            pressPos = self.readEvents()

            self.beginFrame()
            self.drawGrid()

            await self.endFrame(pressPos)

    async def titleScreen(self):
        running = True

        while running:
            pressPos = self.readEvents()

            self.beginFrame()
            self.graphik.drawText("Tic Tac Toe", self.displayWidth//2, self.displayHeight//4, 64, self.black)
            middleButtonXPos = self.displayWidth//2 - 50
            self.drawButton(middleButtonXPos, self.displayHeight - 300, 100, 50, self.black, self.white, 20, "Start", self.gridScreen)
            self.drawQuitButton(middleButtonXPos, self.displayHeight - 100, 100, 50, 20)

            await self.endFrame(pressPos)

if __name__ == "__main__":
    ticTacToe = TicTacToe()
    asyncio.run(ticTacToe.titleScreen())