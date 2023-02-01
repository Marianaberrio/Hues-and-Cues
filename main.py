import sys
import pygame
import time
from collections import defaultdict
import random
from clues import rgb_to_color_clue, clue_to_rgb
from rgb_matrix import board_rgb_matrix, flattened_board_rgb_matrix

class Cell:
    def __init__(self, posx, posy, rgb):
        self.posx = posx # X coordinate of top left corner of the cell
        self.posy = posy # Y coordinate of top left corner of the cell
        self.rgb = rgb # Color in RGB [r,g,b] format of this specific cell

class Board:
    def __init__(self, cell_matrix):
        self.cell_matrix = cell_matrix # cell matrix is a matrix of Cell objects

# def partition is used by the function quicksort_inplace
def partition(player_seq_list, left, right):
  pivot = left
  pivot_value = player_seq_list[pivot][1]
  for i in range(left + 1, right + 1):
    if player_seq_list[i][1] > pivot_value:
        pivot += 1
        player_seq_list[i], player_seq_list[pivot] = player_seq_list[pivot], player_seq_list[i]
  player_seq_list[left], player_seq_list[pivot] = player_seq_list[pivot], player_seq_list[left]
  return pivot

#quicksort function
# O(plog(p)) p = number of players but p can be considered a constant so O(1)
def quicksort_inplace(player_seq_list, left, right):
    if left > right:
        return
    pivot = partition(player_seq_list, left, right)
    quicksort_inplace(player_seq_list, left, pivot - 1)
    quicksort_inplace(player_seq_list, pivot + 1, right)

#binary search for a Red color in a flattened matrix that looks like the following: [[(r,g,b)(index1, index2)], [(r,g,b)(index01, index02],...]
# the flattened matrix is also sorted by red, green and blue values in RGB (in order)
# worst case and average case time complexity O(log(n))  n being the number of color cells in the color matrix
def binary_search(rgb_tuple, left, right):
    # we are looking for index1 and index2 of an rgb_tuple
    while right >= left:
        mid = (left+right)//2
        #compare if we found the whole tuple
        if flattened_board_rgb_matrix[mid][0] == rgb_tuple:
            return flattened_board_rgb_matrix[mid][1]
        elif flattened_board_rgb_matrix[mid][0] > rgb_tuple:
            right = mid - 1
        else:
            left = mid + 1
    #print("Could not find", rgb_tuple)
    return (7, 15) #just in case of any errors the automatic player still makes a default move which is the center of the board

# function receives a matrix of [r,g,b] colors from rgb_matrix.py and translates it into a Board object
# O(n) n being the number of color cells in the color matrix
def from_rgb_to_Board(CELL_SIZE):
    board_cell_matrix = [[0 for _ in range(len(board_rgb_matrix[0]))] for _ in range(len(board_rgb_matrix))]
    # transform each cell in matrix into a Cell object and create board_cell_matrix
    for i in range(len(board_rgb_matrix)):
        for j in range(len(board_rgb_matrix[0])):
            board_cell_matrix[i][j] = Cell(CELL_SIZE * i, CELL_SIZE * j, board_rgb_matrix[i][j])

    # put all these Cell objects into a Board class's cell_matrix
    board = Board(board_cell_matrix)
    return board

# O(p) p = number of players (but p can be considered a constant) so O(1)
def introduce_players():
    print("Instructions: ")
    print("Hues and Cues involves each player selecting the colour based on the rgb number clue and the word clue")
    print("Then the player with the worst guess will go first on the next round. There are as many round as you wish.")
    print("There is also a computer player which will play. The winner is the person who gets closest to the actual colour.")
    print("That means the player with the smallest score is winning.")
    print("You may now input the number of players and begin! ")

    N_PLAYERS = 0
    while N_PLAYERS < 1 or N_PLAYERS > 9:
        try:
            N_PLAYERS = int(input("Enter the number of players (1-9) >> "))
        except ValueError:
            print("The input was not a valid integer.")

    PLAYER_NAMES_SCORES = {}
    for i in range(1, N_PLAYERS+1):
        keep_trying = True
        while keep_trying:
            name = input("Enter a 4 letter nickname for player N{} >> ".format(i))
            if len(name) <= 4 and name not in PLAYER_NAMES_SCORES.keys():
                PLAYER_NAMES_SCORES[name] = 0
                keep_trying = False
            else:
                print("Invalid name! Make sure that it has maximum 4 characters.")

    print("\nLets Begin the Game Now!")
    # adding a bot
    PLAYER_NAMES_SCORES['Bot'] = 0
    return N_PLAYERS+1, PLAYER_NAMES_SCORES

# class Round is the most important class in this game
class Round:
    def __init__(self, true_rgb, true_indexing, screen, player_seq_list, N_PLAYERS, board, CELL_SIZE, PLAYER_NAMES_SCORES, round_scores_hidden, color_clue):
        self.true_rgb = true_rgb  # every round has a true rgb which is a random color chosen by computer
        self.true_indexing = true_indexing  # the random colors indexing (position) in the cell_matrix
        self.screen = screen  # screen we draw on
        self.player_seq_list = player_seq_list  # ordered list of players
        self.N_PLAYERS = N_PLAYERS  # number of players
        self.board = board  # Board instance
        self.CELL_SIZE = CELL_SIZE  # size of cells in the board
        self.PLAYER_NAMES_SCORES = PLAYER_NAMES_SCORES  # dictionary of players and their scores that appear on screen
        self.circle_locations = {}   # locations of players current guesses
        self.round_scores_hidden = round_scores_hidden  # dictionary of players scores which are calculated instantly but not shown on display yet
        self.color_clue = color_clue  # clue for the color

    # round play function that holds all the game logic
    # O(nlogn) where n is the total number of color cells in the matrix
    def play_round(self):
        # empty circles
        self.empty_circle_locations()
        #draw board before the round starts
        self.draw_board_players_clue_circles_on_screen()
        for i in range(self.N_PLAYERS):
            current_player = self.player_seq_list[i][0]
            self.print_whos_turn(current_player)
            not_clicked_on_cell = True
            if current_player == 'Bot':
                time.sleep(1)
                # O(nlogn)
                self.bots_move()
                not_clicked_on_cell = False
            while not_clicked_on_cell:
                for event in pygame.event.get():
                    if event.type == pygame.MOUSEBUTTONUP:
                        pos = pygame.mouse.get_pos()

                        if self.inside_board(pos) and (pos[0]//self.CELL_SIZE, pos[1]//self.CELL_SIZE) not in self.circle_locations.values():
                            self.circle_locations[current_player] = (pos[0]//self.CELL_SIZE, pos[1]//self.CELL_SIZE)
                            self.calculate_distance_from_real_color((pos[0]//self.CELL_SIZE, pos[1]//self.CELL_SIZE), current_player)
                            not_clicked_on_cell = False
                        else:
                            print("The click was outside the board or on top of other players circle. Choose the spot wisely.")

                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()

            # O(n)
            self.draw_board_players_clue_circles_on_screen()

        self.update_scores()
        self.display_actual_color()
        time.sleep(4)

    # O(p) p = number of players but can be considered constant so O(1)
    def empty_circle_locations(self):
        for name in self.PLAYER_NAMES_SCORES:
            self.circle_locations[name] = -1

    # O(p) p = number of players but can be considered constant so O(1)
    def update_scores(self):
        for key in self.round_scores_hidden.keys():
            self.PLAYER_NAMES_SCORES[key] = self.round_scores_hidden[key]

    # O(1)
    def calculate_distance_from_real_color(self, indexes, current_player):
        self.round_scores_hidden[current_player] += (abs(self.true_indexing[0]-indexes[0])+abs(self.true_indexing[1] - indexes[1]))

    # O(1)
    def display_actual_color(self):
        x = self.true_indexing[0]*self.CELL_SIZE
        y = self.true_indexing[1]*self.CELL_SIZE
        pygame.draw.rect(self.screen, "black", pygame.Rect(x, y, self.CELL_SIZE, self.CELL_SIZE), 3)
        pygame.display.flip()
        time.sleep(2)

    # O(nlogn) n being total number of color cells
    def bots_move(self):
        rand_rgb_index = random.randint(0, len(clue_to_rgb[self.color_clue])-1)
        bots_rgb_tuple = clue_to_rgb[self.color_clue][rand_rgb_index]
        pos = binary_search(bots_rgb_tuple, 0, len(flattened_board_rgb_matrix)-1)

        self.circle_locations['Bot'] = (pos[0], pos[1])
        self.calculate_distance_from_real_color((pos[0], pos[1]), 'Bot')

    # O(1) - checks if the mouse click was valid (inside the board)
    def inside_board(self, pos):
        return (pos[0] >= 0 and pos[0] <= 320 and pos[1] >= 0 and pos[1] <= 600)

    # O(1) - displays whos turn it is on the screen
    def print_whos_turn(self, current_player):
        font = pygame.font.Font(pygame.font.get_default_font(), 26)
        text_surface = font.render("{}'s turn".format(current_player), True, (200, 200, 200))
        self.screen.blit(text_surface, dest=(330, 550))
        pygame.display.update()

    # prints all the vital parts on the board
    # O(n) where n is the number of color cells in a matrix
    def draw_board_players_clue_circles_on_screen(self):
        self.screen.fill('black')

        for i in range(len(self.board.cell_matrix)):
            for j in range(len(self.board.cell_matrix[0])):
                posx = self.board.cell_matrix[i][j].posx
                posy = self.board.cell_matrix[i][j].posy
                color = self.board.cell_matrix[i][j].rgb
                pygame.draw.rect(self.screen, color, pygame.Rect(posx, posy, self.CELL_SIZE, self.CELL_SIZE))
        # draw the text Clue on screen
        font = pygame.font.Font(pygame.font.get_default_font(), 26)
        text_surface = font.render('Clue N1: {}'.format(self.color_clue), True, (255, 255, 255))
        self.screen.blit(text_surface, dest=(330, 20))
        font = pygame.font.Font(pygame.font.get_default_font(), 26)
        text_surface = font.render('Clue N2: {}'.format(self.true_rgb), True, (255, 255, 255))
        self.screen.blit(text_surface, dest=(330, 50))
        pygame.display.flip()

        # print Players
        line = 100
        for name in self.PLAYER_NAMES_SCORES.keys():
            font = pygame.font.Font(pygame.font.get_default_font(), 26)
            text_surface = font.render('{} - {}'.format(name, PLAYER_NAMES_SCORES[name]), True, (255, 255, 255))
            self.screen.blit(text_surface, dest=(330, line))
            line += 40

        # draw circles
        for key in self.circle_locations.keys():
            if self.circle_locations[key] != -1:
                if key == 'Bot':
                    color = "white"
                else: color = "black"
                matrix_index = self.circle_locations[key]
                cen_pos = (matrix_index[0]*self.CELL_SIZE+self.CELL_SIZE//2, matrix_index[1]*self.CELL_SIZE+self.CELL_SIZE//2)
                pygame.draw.circle(self.screen, color, cen_pos, 10)

        # display flip
        pygame.display.flip()

# Initiates rounds
# O(r*n) where r is number of rounds and n is the number of color cells in the matrix
def main(N_PLAYERS, PLAYER_NAMES_SCORES):
    WINDOWWIDTH, WINDOWHEIGHT = 640, 600
    CELL_SIZE = 20

    pygame.init()
    screen = pygame.display.set_mode((WINDOWWIDTH, WINDOWHEIGHT))
    pygame.display.set_caption('Hues & Cues')

    #transforming a matrix of rgb into Board class (which has a cell matrix)
    board = from_rgb_to_Board(CELL_SIZE)
    round_scores_hidden = defaultdict(int)

    while True:
        #randomly choose a cell in the board
        rand_col = random.randint(0, len(board.cell_matrix[0])-1) #(0-30)
        rand_row = random.randint(0, len(board.cell_matrix)-1) #(0-16)
        rand_rgb = board.cell_matrix[rand_row][rand_col]
        color_clue = rgb_to_color_clue[tuple(rand_rgb.rgb)]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        player_seq_list = []
        for key, value in PLAYER_NAMES_SCORES.items():
            player_seq_list.append((key, value))
        quicksort_inplace(player_seq_list, 0, N_PLAYERS-1)
        one_round = Round(rand_rgb.rgb, [rand_row, rand_col], screen, player_seq_list, N_PLAYERS, board, CELL_SIZE, PLAYER_NAMES_SCORES, round_scores_hidden, color_clue)
        one_round.play_round()

if __name__ == "__main__":
    N_PLAYERS, PLAYER_NAMES_SCORES = introduce_players()
    main(N_PLAYERS, PLAYER_NAMES_SCORES)
