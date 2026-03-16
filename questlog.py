import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import sqlite3

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN") #this token is grabbed form a .env file that is not included in the GitHub repo

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def initialize_database():
    # Connects to database or creates it if it doesnt exist
    conn = sqlite3.connect("quests.db")
    cursor = conn.cursor()

    # Creates the quest table in the file if it doesnt exist 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quests (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   title TEXT NOT NULL,
                   description TEXT NOT NULL,
                   creator_id INTEGER NOT NULL,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   status TEXT DEFAULT 'active'
        )

    """)
    # Save changes and close connection
    conn.commit()
    conn.close()

# Add quest to database
def create_quest(title, description, creator_id):
    conn = sqlite3.connect("quests.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO quests (title, description, creator_id)
        VALUES (?, ?, ?)
""", (title, description, creator_id))
    
    # Save changes and close connection
    conn.commit()
    conn.close()

# View all the quests
def get_all_quests():
    conn = sqlite3.connect("quests.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, description, creator_id, created_at FROM quests")
    quests = cursor.fetchall()

    conn.close()
    return quests        

def complete_quest(quest_id):
    conn = sqlite3.connect("quests.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE quests SET status = ? WHERE id = ?",
        ("completed", quest_id)
    )
    conn.commit()
    conn.close()

# Creates the board that displays all the quests
def build_quest_embed():
    quests = get_all_quests()

    embed = discord.Embed(
        title="Quest Board",
        description="Available quests:",
        color=discord.Color.dark_gold()
    )

    if not quests:
        embed.description = "Add some quests then come back."
        return embed
    
    for quest in quests:
        quest_id = quest[0]
        title = quest[1]
        description = quest[2]

        embed.add_field(
            name=f"#{quest_id} - {title}",
            value=description,
            inline=False
        )

    return embed

# Delete quest
def delete_quest(quest_id):
    conn = sqlite3.connect("quests.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM quests WHERE id = ?", (quest_id,)) 

    conn.commit()
    conn.close()

def get_quest_by_id(quest_id):
    conn = sqlite3.connect("quests.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, title, description, creator_id, created_at FROM quests WHERE id = ?", (quest_id,)
    )

    quest = cursor.fetchone()
    conn.close()
    return quest

# Logic functions for the buttons
async def add_quest_logic(interaction: discord.Interaction):
    await interaction.response.send_message(
        
        "Adding quest...", 
        ephemeral=True
        )

async def delete_quest_logic(interaction: discord.Interaction):
    await interaction.response.send_message("Deleting quest...", ephemeral=True)

async def view_quests_logic(interaction: discord.Interaction):
    quests = get_all_quests()

    embed = build_quest_embed()
    
    if not quests:
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    view = discord.ui.View()
    view.add_item(QuestSelect(quests))

    await interaction.response.send_message(embed=embed, ephemeral=True)

async def cancel_logic(interaction: discord.Interaction):
    await interaction.response.send_message("Cancelled", ephemeral=True)

class AddQuestModal(discord.ui.Modal, title="Add a New Quest"):

    quest_title = discord.ui.TextInput(
        label="Quest Title",
        placeholder="Enter the quest title...",
        max_length=100
    )

    quest_description = discord.ui.TextInput(
        label="Quest Description",
        placeholder="Describe the quest...",
        style=discord.TextStyle.paragraph,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        title = self.quest_title.value
        description = self.quest_description.value
        creator_id = interaction.user.id


        # Save to database
        create_quest(title, description, creator_id)
        
        #Confirms that the quest was created
        await interaction.response.send_message(
            f"Quest Created!\n\nTitle: {title}\nDescription: {description}", ephemeral=True
        )

        #Saves the info to the database (will be added later)

class MenuView(discord.ui.View): # makes the menu using the ui options in discord 
    def __init__(self, author):
        super().__init__(timeout=30) #after 30 sec the menu becomes invalid
        self.author = author        

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message(
                   "This menu isn't for you",
                   ephemeral=True
                )
            return False
        return True

    # Buttons for the menu, defines and calls the connected function 
    @discord.ui.button(label="Add Quest", style=discord.ButtonStyle.blurple)
    async def add_quest_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddQuestModal())

    @discord.ui.button(label="Delete Quest", style=discord.ButtonStyle.blurple)
    async def delete_quest_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await delete_quest_logic(interaction)

    @discord.ui.button(label="View All Quests", style=discord.ButtonStyle.gray)
    async def show_quests_button(self, interaction:discord.Interaction, button: discord.ui.Button):
        await view_quests_logic(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
         await cancel_logic(interaction)

class QuestActionView(discord.ui.View):
    def __init__(self, quest_id: int):
        super().__init__(timeout=60)
        self.quest_id = quest_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Restric actions to quest creator
        quest = get_quest_by_id(self.quest_id)

        if not quest:
            await interaction.response.send_message(
                "This quest no longer exists.",
                ephemeral=True
            )
            return False
        
        creator_id = quest[3]

        if interaction.user.id != creator_id:
            await interaction.response.send_message(
                "That is not one of your quests",
                ephemeral=True
            )
            return False
        
        return True
    
    @discord.ui.button(label="Edit", style=discord.ButtonStyle.grey)
    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"Editing quest #{self.quest_id} (work in progress)",
            ephemeral=True
        )

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.red)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        delete_quest(self.quest_id)

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=f"Quest #{self.quest_id} has been deleted.",
            view=self
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="Action cancelled.",
            view=self
        )
class QuestSelect(discord.ui.Select):
    def __init__(self, quests):
        options = []

        for quest in quests:
            quest_id = quest[0]
            title = quest[1]
            description = quest[2]

            short_desc = description[:97] + "..." if len(description) > 100 else description

            options.append(
                discord.SelectOption(
                    label=f"{title}",
                    description=short_desc,
                    value=str(quest_id)
                )
            )
        
        super().__init__(
            placeholder="Choose a quest to manage...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_quest_id = int(self.values[0])

        action_view = QuestActionView(selected_quest_id)

        await interaction.response.send_message(
            f"Selected quest ID **{selected_quest_id}**.",
            view=action_view,
            ephemeral=True
        )

@bot.event
async def on_member_join(member):
    print("Welcome")

@bot.tree.command(name="menu", description="Main menu for QuestLog")
async def menu(interaction:discord.Interaction):
    view = MenuView(interaction.user)
    await interaction.response.send_message(
        """
Welcome to QuestLog
What would you like to do?
        """, view=view
    )

@bot.event
async def on_ready():
    initialize_database()

    await bot.tree.sync()
    print(f"{bot.user} is online")

bot.run(TOKEN)