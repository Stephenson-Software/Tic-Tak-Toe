import asyncio
import sys
import time

import pygame
import random
from preponderous.graphik import Graphik


def runningInBrowser():
    # pygbag runs the game under CPython compiled to WebAssembly
    return sys.platform == "emscripten"


def ignoreHeldButton():
    # Graphik.drawButton calls its function on every frame the left button is held over the
    # box, and it cannot await the game's handlers; a button is pressed from the press event
    # in TicTacToe.endFrame instead
    pass


def pressLandedOn(pressPos, xpos, ypos, width, height):
    # the same bounds Graphik.drawButton uses for the cursor: exactly the drawn box, so its
    # left and top edges count and the right and bottom ones (one past the box) do not
    return pressPos is not None and xpos <= pressPos[0] < xpos + width and ypos <= pressPos[1] < ypos + height


# The cells of each line of three, as the TicTacToe attributes holding their marks
LINES = [
    ("topLeftL", "topMiddleL", "topRightL"),
    ("middleLeftL", "middleMiddleL", "middleRightL"),
    ("bottomLeftL", "bottomMiddleL", "bottomRightL"),
    ("topLeftL", "middleLeftL", "bottomLeftL"),
    ("topMiddleL", "middleMiddleL", "bottomMiddleL"),
    ("topRightL", "middleRightL", "bottomRightL"),
    ("topLeftL", "middleMiddleL", "bottomRightL"),
    ("topRightL", "middleMiddleL", "bottomLeftL"),
]

# The strip above the board where drawGrid says whose turn it is
STATUS_STRIP_HEIGHT = 110
STATUS_Y = 60
STATUS_TEXT_SIZE = 32
# The title screen's one line of instructions
TITLE_HOW_TO_PLAY = "You are X: get three in a row."

# The cells of a line of three, once there is one
WIN_SLOT_COLOR = (255, 215, 0)


#  @author Daniel McCoy Stephenson
#  @since August 6th, 2022
class TicTacToe:
    framesPerSecond = 60
    startPauseSeconds = 0.5

    def __init__(self):
        if runningInBrowser():
            # every page load would otherwise start from the same random state, so each
            # visitor would face the same sequence of computer moves
            random.seed(time.time_ns())

        self.black = (0,0,0)
        self.white = (255,255,255)

        self.displayWidth = 800
        self.displayHeight = 600

        self.initializeDisplay()

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

    def initializeDisplay(self):
        # The 2D window. The 3D view (strata_view/game.py) replaces this with a Strata window and
        # keeps every screen, button and rule below as it is
        pygame.init()

        self.gameDisplay = pygame.display.set_mode((self.displayWidth, self.displayHeight))

        self.graphik = Graphik(self.gameDisplay)

        pygame.display.set_caption("Tic Tac Toe")

        self.clock = pygame.time.Clock()

    def presentNow(self):
        # shows what has been drawn so far, between frames (drawGrid shows the player's mark
        # before the computer's one-second pause)
        pygame.display.update()

    def drawGridSlot(self, xpos, ypos, XorO, function):
        # a cell in the line of three that ended the game is gold, so the board shows how
        won = self.winningLine()
        attribute = function.__name__ + "L"
        colorBox = WIN_SLOT_COLOR if won is not None and attribute in won[1] else self.white
        self.drawButton(xpos, ypos, 100, 100, colorBox, self.black, 64, XorO, function)

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
        # The board is still shown during a one-second pause, and a tap made then was aimed at the
        # board as it stood. Left queued, it would be handled when the pause ends: after the
        # computer's pause it would be played as the player's next move before the computer's
        # mark was seen, and after an end screen's pause it would press the button drawn where it
        # landed (Play Again covers the bottom-middle cell)
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

    async def pause(self, seconds):
        # every pause the game makes (the computer's move, the end screens, after Start); the
        # board stays on screen and the browser keeps running. The browser's 3D view
        # (strata_view/web.py) keeps itself up to date during one
        await asyncio.sleep(seconds)

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
            await self.pause(1)
            self.discardPressesMadeDuringThePause()

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

        self.drawStatus()
        self.presentNow()

    def winningLine(self):
        # (mark, the line's three cell attributes) for a line of three, or None
        for line in LINES:
            marks = {getattr(self, attribute) for attribute in line}
            if len(marks) == 1 and marks != {""}:
                return marks.pop(), line
        return None

    def statusText(self):
        # Whose turn it is, read from the board: the player (X) always moves first, so after the
        # player's move there is one more X than O and the computer is about to move
        won = self.winningLine()
        if won is not None:
            return "You got three in a row!" if won[0] == "X" else "The computer got three in a row."
        marks = [getattr(self, attribute) for line in LINES[:3] for attribute in line]
        if "" not in marks:
            return "The board is full."
        if marks.count("X") > marks.count("O"):
            return "The computer (O) is thinking..."
        return "Your turn: you are X"

    def drawStatus(self):
        # The board is redrawn mid-frame (a move, then the computer's), so the strip is cleared
        # before the line is written over it
        self.graphik.drawRectangle(0, 0, self.displayWidth, STATUS_STRIP_HEIGHT, self.white)
        self.graphik.drawText(self.statusText(), self.displayWidth//2, STATUS_Y, STATUS_TEXT_SIZE, self.black)

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
        await self.pause(1)
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
        await self.pause(1)
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
        await self.pause(1)
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

    async def startGame(self):
        # The Start button is drawn over the centre cell, and a press made after the board appears
        # is a new press to the grid screen, so the second press of a double-click on Start would
        # play the player's first move. Half a second covers a double-click, and it is too short
        # for a player to have seen the board and aimed at a cell
        self.beginFrame()
        self.drawGrid()
        await self.pause(self.startPauseSeconds)
        self.discardPressesMadeDuringThePause()
        await self.gridScreen()

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
            # what the game is, before Start: who the player is and how a game is won
            self.graphik.drawText(TITLE_HOW_TO_PLAY, self.displayWidth//2, self.displayHeight//4 + 70, 24, self.black)
            middleButtonXPos = self.displayWidth//2 - 50
            self.drawButton(middleButtonXPos, self.displayHeight - 300, 100, 50, self.black, self.white, 20, "Start", self.startGame)
            self.drawQuitButton(middleButtonXPos, self.displayHeight - 100, 100, 50, 20)

            await self.endFrame(pressPos)

# Strata ships libraries for desktop Linux and Windows, so the 3D view is the default there
STRATA_PLATFORMS = ("linux", "win32")


def parseArguments(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="Play Tic Tac Toe against the computer.")
    view = parser.add_mutually_exclusive_group()
    view.add_argument("--2d", dest="flat", action="store_true",
                      help="play in the 2D window instead of the 3D one")
    view.add_argument("--strata", action="store_true",
                      help="insist on the 3D window: stop with the reason if it can't start, "
                           "instead of falling back to 2D")
    return parser.parse_args(argv)


def chooseInterface(args, platform=None):
    # "3d" or "2d". 3D is the default on Linux and Windows desktops; the browser build doesn't
    # come through here (it starts from main.py)
    platform = sys.platform if platform is None else platform
    if args.flat:
        return "2d"
    if args.strata or platform in STRATA_PLATFORMS:
        return "3d"
    return "2d"


def main(argv=None):
    args = parseArguments(argv)
    if chooseInterface(args) == "3d":
        from strata_view import StrataUnavailable, runStrataGame

        try:
            runStrataGame()
            return
        except StrataUnavailable as reason:
            if args.strata:
                sys.exit("The 3D window couldn't start: %s." % reason)
            print(
                "The 3D view isn't available here: %s.\n"
                "Starting the 2D game instead (--2d skips this check)." % reason
            )
    ticTacToe = TicTacToe()
    asyncio.run(ticTacToe.titleScreen())


if __name__ == "__main__":
    main()
