import pygame
import time
import random
from Graphik import Graphik


#  @author Daniel McCoy Stephenson
#  @since August 6th, 2022
class TicTacToe:
    def __init__(self):
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

    def drawGridSlot(self, xpos, ypos, XorO, function):
        self.graphik.drawButton(xpos, ypos, 100, 100, self.white, self.black, 64, XorO, function)

    def exit(self):
        pygame.quit()
        quit()

    def topLeft(self):
        if self.topLeftL == "":
            self.topLeftL = "X"
            self.drawGrid()
            self.moves += 1
            self.computerTurn()

    def topMiddle(self):
        if self.topMiddleL == "":
            self.topMiddleL = "X"
            self.drawGrid()
            self.moves += 1
            self.computerTurn()

    def topRight(self):
        if self.topRightL == "":
            self.topRightL = "X"
            self.drawGrid()
            self.moves += 1
            self.computerTurn()

    def middleLeft(self):
        if self.middleLeftL == "":
            self.middleLeftL = "X"
            self.drawGrid()
            self.moves += 1
            self.computerTurn()

    def middleMiddle(self):
        if self.middleMiddleL == "":
            self.middleMiddleL = "X"
            self.drawGrid()
            self.moves += 1
            self.computerTurn()

    def middleRight(self):
        if self.middleRightL == "":
            self.middleRightL = "X"
            self.drawGrid()
            self.moves += 1
            self.computerTurn()

    def bottomLeft(self):
        if self.bottomLeftL == "":
            self.bottomLeftL = "X"
            self.drawGrid()
            self.moves += 1
            self.computerTurn()    

    def bottomMiddle(self):
        if self.bottomMiddleL == "":
            self.bottomMiddleL = "X"
            self.drawGrid()
            self.moves += 1
            self.computerTurn()  

    def bottomRight(self):
        if self.bottomRightL == "":
            self.bottomRightL = "X"
            self.drawGrid()
            self.moves += 1
            self.computerTurn()  

    def computerTurn(self):
        self.checkForWinCondition()
        
        if self.moves != 9:
            time.sleep(1)

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
        self.checkForWinCondition()
        
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

        self.drawGridSlot(centerGridX - 125, centerGridY + 125, self.bottomLeftL, self.bottomLeft) # top row left column
        self.drawGridSlot(centerGridX, centerGridY + 125, self.bottomMiddleL, self.bottomMiddle) # top row middle column
        self.drawGridSlot(centerGridX + 125, centerGridY + 125, self.bottomRightL, self.bottomRight) # top row right column
        
        pygame.display.update()

    def restart(self):
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
        self.titleScreen()

    def playerWin(self):
        time.sleep(1)

        while self.moves > 0:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()
            
                self.gameDisplay.fill(self.white)
                self.graphik.drawText("You won!", self.displayWidth//2, self.displayHeight//4, 64, self.black)
                middleButtonXPos = self.displayWidth//2 - 50
                self.graphik.drawButton(middleButtonXPos, self.displayHeight - 200, 100, 50, self.black, self.white, 16, "Play Again", self.restart)
                self.graphik.drawButton(middleButtonXPos, self.displayHeight - 100, 100, 50, self.black, self.white, 16, "Quit", exit)

                pygame.display.update()
        
    def computerWin(self):
        time.sleep(1)

        while self.moves > 0:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()
            
                self.gameDisplay.fill(self.white)
                self.graphik.drawText("You lost!", self.displayWidth//2, self.displayHeight//4, 64, self.black)
                middleButtonXPos = self.displayWidth//2 - 50
                self.graphik.drawButton(middleButtonXPos, self.displayHeight - 200, 100, 50, self.black, self.white, 20, "Play Again", self.restart)
                self.graphik.drawButton(middleButtonXPos, self.displayHeight - 100, 100, 50, self.black, self.white, 20, "Quit", exit)

                pygame.display.update()
                
    def tie(self):
        time.sleep(1)

        while self.moves > 0:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()
            
                self.gameDisplay.fill(self.white)
                self.graphik.drawText("You lost!", self.displayWidth//2, self.displayHeight//4, 64, self.black)
                middleButtonXPos = self.displayWidth//2 - 50
                self.graphik.drawButton(middleButtonXPos, self.displayHeight - 200, 100, 50, self.black, self.white, 20, "Play Again", self.restart)
                self.graphik.drawButton(middleButtonXPos, self.displayHeight - 100, 100, 50, self.black, self.white, 20, "Quit", exit)

                pygame.display.update()

    def checkForWinCondition(self):
        # case top row
        if self.topLeftL == "X" and self.topMiddleL == "X" and self.topRightL == "X":
            self.playerWin()
            
        if self.topLeftL == "O" and self.topMiddleL == "O" and self.topRightL == "O":
            self.computerWin()
        
        # case middle row
        if self.middleLeftL == "X" and self.middleMiddleL == "X" and self.middleRightL == "X":
            self.playerWin()
            
        if self.middleLeftL == "O" and self.middleMiddleL == "O" and self.middleRightL == "O":
            self.computerWin()
        
        # case bottom row
        if self.bottomLeftL == "X" and self.bottomMiddleL == "X" and self.bottomRightL == "X":
            self.playerWin()
            
        if self.bottomLeftL == "O" and self.bottomMiddleL == "O" and self.bottomRightL == "O":
            self.computerWin()
        
        # case left column
        if self.topLeftL == "X" and self.middleLeftL == "X" and self.bottomLeftL == "X":
            self.playerWin()
            
        if self.topLeftL == "O" and self.middleLeftL == "O" and self.bottomLeftL == "O":
            self.computerWin()
        
        # case middle column
        if self.topMiddleL == "X" and self.middleMiddleL == "X" and self.bottomMiddleL == "X":
            self.playerWin()
            
        if self.topMiddleL == "O" and self.middleMiddleL == "O" and self.bottomMiddleL == "O":
            self.computerWin()
        
        # case right column
        if self.topRightL == "X" and self.middleRightL == "X" and self.bottomRightL == "X":
            self.playerWin()
            
        if self.topRightL == "O" and self.middleRightL == "O" and self.bottomRightL == "O":
            self.computerWin()
        
        # case diagonal ->
        if self.topLeftL == "X" and self.middleMiddleL == "X" and self.bottomRightL == "X":
            self.playerWin()
            
        if self.topLeftL == "O" and self.middleMiddleL == "O" and self.bottomRightL == "O":
            self.computerWin()
            
        # case diagonal <-
        if self.topRightL == "X" and self.middleMiddleL == "X" and self.bottomLeftL == "X":
            self.playerWin()
            
        if self.topRightL == "O" and self.middleMiddleL == "O" and self.bottomLeftL == "O":
            self.computerWin()
            
        if self.moves == 9:
            self.tie()

    def gridScreen(self):
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()
                    
                self.gameDisplay.fill(self.white)
                
                self.drawGrid()

    def titleScreen(self):
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()
            
                self.gameDisplay.fill(self.white)
                self.graphik.drawText("Tic Tac Toe", self.displayWidth//2, self.displayHeight//4, 64, self.black)
                middleButtonXPos = self.displayWidth//2 - 50
                self.graphik.drawButton(middleButtonXPos, self.displayHeight - 300, 100, 50, self.black, self.white, 20, "Start", self.gridScreen)
                self.graphik.drawButton(middleButtonXPos, self.displayHeight - 100, 100, 50, self.black, self.white, 20, "Quit", exit)

                pygame.display.update()

ticTacToe = TicTacToe()
ticTacToe.titleScreen()