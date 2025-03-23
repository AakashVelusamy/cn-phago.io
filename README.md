# phago.io

## Developed by
- 23PT01 - Aakash Velusamy  
- 23PT14 - Kabilan S  

## What is phago.io ?

The moment you jump into an online game, computer networks come into action - bringing players together, tracking every moves out there, and making sure everyone sees the same game. That’s what we built with phago.io, a multiplayer game inspired by Agar.io, developed using Python with Pygame and Socket Programming. You move a blob, eat food to grow, and fight for the highest score in a five minute match - whoever has the most points wins. A server runs the game, handling all player actions and swapping data between players instantly. The camera zooms in and out to keep your blob in view, and we kept the rules simple so it’s easy to jump in and play.

---

## Key Features

### • How Networking Works Here
| Part                  | What’s Happening                                                                 |
|-----------------------|----------------------------------------------------------------------------------|
| **What It Is**        | The game uses the internet to connect players to a main computer called a server. |
| **Why It Matters**    | It lets many players join the same game and play together from different places. |
| **How We Did It**     | We used TCP sockets to connect the server and players. The server keeps track of all blobs, food, and scores, and sends this info to everyone. |
| **More Details**      | Each player sends their mouse position to the server. The server updates the game - like moving blobs or adding points when food is eaten - and sends the new game state to all players every 0.01 seconds. We used a tool called `pickle` to turn the game info into small messages that travel fast. |

Networking is the main part of our game. It’s how your computer talks to the server, and how the server talks to all players. When one player moves or eats food, the server makes sure everyone sees it right away. We had to make sure messages don’t get lost and everyone stays on the same page, which is a big part of computer networks.

---

### • How the Camera Works
| Part                  | What’s Happening                                                                 |
|-----------------------|----------------------------------------------------------------------------------|
| **What It Is**        | The camera follows your blob and zooms in or out based on your blob’s size.     |
| **Why It Matters**    | It makes sure you can always see your blob clearly without zooming too often.  |
| **How We Did It**     | We set limits: if your blob gets bigger than a certain size (like 50), the camera zooms out. If it gets smaller than another size (like 20), it zooms in. After zooming, we change these limits so it doesn’t zoom again too soon. |
| **More Details**      | For example, if your blob grows to 60, the camera zooms out, and the new “big size” becomes 90. It won’t zoom out again until your blob is bigger than 90. This stops the camera from zooming in and out all the time, which used to make the game harder to play. |

The camera helps you see your blob better. It keeps your blob in the middle of the screen and only zooms when it needs to, so the game feels smoother.

---

### • How the Game Rules Work
| Part                  | What’s Happening                                                                 |
|-----------------------|----------------------------------------------------------------------------------|
| **What It Is**        | The rules that decide how blobs move, grow, and how the game ends.            |
| **Why It Matters**    | It makes the game fair and easy to understand for all players.               |
| **How We Did It**     | Your blob moves toward your mouse. If you stop moving the mouse, it keeps going in the last direction. When your blob touches food, it eats it, grows bigger, and gets points. The game lasts 5 minutes, and the player with the most points wins. |
| **More Details**      | We made sure your blob doesn’t get stuck when it touches food - it eats it as soon as the edges touch. If one blob eats another, the bigger one grows, and the smaller one starts over. The game shows a leaderboard, your score, a timer, and a minimap to help you play better. |

The game rules make sure everything works as it should. You move your blob with the mouse, eat food to grow, and aim for the highest score. At the end, the game shows who won, and everyone can see their results.

---

## How the Game Runs

1. **Start the Server**: The server starts and waits for players to join.
2. **Players Join**: Each player starts the game, enters the server’s details, and picks a username.
3. **Playing the Game**:
   - Move your blob with the mouse to eat food and grow.
   - The server shares where blobs and food are with everyone.
   - The camera zooms in or out to keep your blob clear.
4. **Game Ends**: After 5 minutes, the player with the most points wins, and the game shows the winner.
5. **Clean Up**: The game closes connections and shuts down properly.

This is how the game uses networking, the camera, and rules to work together.

---

## How to Play 
### On the Server Computer
```bash
python server.py
```
- It’ll ask for an IP and port. Press Enter to use your computer’s IP and port 1401.

### On Your Computer
```bash
python client.py
```
- A window will open. Type the server’s IP, port (1401), and your username. Press Enter to start.

### What the Server Shows
```
2025-03-23 08:00:00 - INFO - Server running on 192.168.0.202:1401
2025-03-23 08:00:05 - INFO - New connection from ('127.0.0.1', 54321)
2025-03-23 08:00:05 - INFO - First player joined, starting game timer
2025-03-23 08:00:05 - INFO - Added player 0: AK
2025-03-23 08:00:10 - DEBUG - Player 0 moved to (300.5, 400.2)
2025-03-23 08:00:15 - DEBUG - Player 0 ate food at (310.0, 405.0)
```

### What You See
- A game window (960x720) opens with your blob, food, and other players.
- On the screen:
  - Leaderboard at top left (like “AK: 50”).
  - Timer at top center (like “Time: 04:55”).
  - Your score at top right (like “Score: 50”).
  - Minimap at bottom left.
  - Our watermark at bottom right (“phago.io - 23PT01 - 23PT14”).
- After 5 minutes, it shows the winner (like “Winner: AK with 150 points!”).

---

## Summary
In building phago.io, we made a multiplayer game where players' actions are shared right away. This project taught us about networking, handling data, and making sure that everything works well when multiple users are involved.

---

*Made for 23XT46 - Computer Networks Lab - IV Semester*
