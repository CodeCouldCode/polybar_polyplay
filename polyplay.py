#! /usr/bin/python3

import re
import time
import os
import signal
import subprocess

from typing import Dict, Literal


class Config:
    """Configs for the PolyPlay module that users can chage."""

    # Determins what color the `control_icons` and `player_icons` will be
    # Make sure the hex is in lower case!
    color: str = "#000000"
    # Currently supports the following controls
    control_icons: Dict[str, str] = {
        "play": "󰐊",
        "pause": "",
        "previous": "󰒮",
        "next": "󰒭",
    }
    # Extend this field with player name and its icon.
    player_icons: Dict[str, str] = {
        "firefox": " ",
        "brave": " ",
        "vlc": "󰕼 ",
        "spotify": " ",
        "default": " ",  # Do NOT remove this
    }
    # This len excludes the len of controls and icons
    scrolling_msg_len: int = 15
    # This determins the scrolling speed
    update_interval: float = 0.3
    # If you wish to display languages other than english, make
    # sure to include that in your polybar configuration.
    # Refer to README for more information.
    english_text_only: bool = False
    # Color for both icons and player controls
    # Message to show in certain situations.
    default_text: str = "default text"
    error_text: str = "error text"


class Utils:
    @classmethod
    def center_text(cls, text_to_center: str, msg_display_len: int) -> str:
        """Pads or truncates the text so it appears to be in the center of
        the polybar module.

        If longer than `msg_display_len`, then the text will be truncated.
        If less than `msg_display_len`, then the text will be padded on both sides.
        """
        if len(text_to_center) >= msg_display_len:
            return text_to_center[:msg_display_len]
        left_padding = " " * ((msg_display_len - len(text_to_center)) // 2)
        right_padding = " " * (
            msg_display_len - (len(left_padding) + len(text_to_center)) - 1
        )
        return f"{left_padding}{text_to_center}{right_padding}"

    @classmethod
    def is_english(cls, text_to_check: str) -> bool:
        try:
            text_to_check.encode(encoding="utf-8").decode("ascii")
        except UnicodeDecodeError:
            return False
        return True

    @classmethod
    def clean_track_title(cls, title_to_clean: str) -> str:
        """Clean the track title.

        This is mainly for VLC titles.

        TODO:
            Properly handle URL encodings.
        """
        return re.sub(r"%20", " ", title_to_clean.split("/")[-1])

    @classmethod
    def colorize_string(cls, str_to_color: str, color: str) -> str:
        """Uses polybar `Format tags -> Foreground color` to change the strings color."""

        return f"%{{F{color}}} {str_to_color} %{{F-}}"

    @classmethod
    def actionize_string(
        cls,
        str_to_action: str,
        command: str,
        trigger: Literal[
            "left click",
            "middle click",
            "right click",
            "scroll up",
            "scroll down",
            "double left click",
            "double middle click",
            "double right click",
        ] = "left click",
    ) -> str:
        """Uses polybar `Format tags -> Action` to actionize the string.

        Documentation: https://github.com/polybar/polybar/wiki/Formatting

        You can nest actions by calling this function on the already
            actionized string.
        """

        trigger_mapping = {
            "left click": 1,
            "middle click": 2,
            "right click": 3,
            "scroll up": 4,
            "scroll down": 5,
            "double left click": 6,
            "double middle click": 7,
            "double right click": 8,
        }

        action = trigger_mapping.get(trigger, 1)

        return f"%{{A{action}:{command}:}}{str_to_action}%{{A}}"


class Player:
    """Represents a player instance."""

    def __init__(self, player_name: str, config: Config) -> None:
        self.player_name = player_name
        self.config = config
        # This will be updated and assigned from PolyPlay
        self.display_text: str = ""
        # This will be updated from Polyplay
        self.display_text_start_index: int = 0

    @property
    def is_playing(self) -> bool:
        """Whether the player is currently playing media."""

        status = subprocess.check_output(
            ["playerctl", "-p", self.player_name, "status"]
        )
        return True if status.decode("utf-8").rstrip() == "Playing" else False

    @property
    def is_stopped(self) -> bool:
        """Whether the player is currently stopped.

        This is a bit of an interesting case. When a web browser starts playing media,
        a player is created. When the tab that plays the media is closed, the player
        still exists, but is marked as `stopped`. If you then open another tab and
        start playing media, the same player will then be shown as playing. The player
        will only stop existing if the browser is closed entirelly.
        """

        status = subprocess.check_output(
            ["playerctl", "-p", self.player_name, "status"]
        )
        return True if status.decode("utf-8").rstrip() == "Stopped" else False

    @property
    def exists(self) -> bool:
        """Whether the player still exists."""

        available_players = Player.get_available_players()
        return True if self.player_name in available_players else False

    @property
    def metadata(self) -> str:
        """Track / media name and artist."""

        if not self.exists:
            return ""

        metadata = (
            subprocess.check_output(
                [
                    "playerctl",
                    "-p",
                    self.player_name,
                    "metadata",
                    "--format",
                    r"'{{title}},{{artist}},{{xesam:url}}",
                ]
            )
            .decode("utf-8")
            .split(",")
        )
        # In case comamnd returns error
        if len(metadata) < 3:
            # Can be more than 3 in case of multiple artists
            return Utils.center_text(
                self.config.error_text, self.config.scrolling_msg_len
            )
        # There can be more than 1 artist
        title, *artists, vlc_title = metadata
        title = title if title != "" else vlc_title
        # Artist metadata might not always be available
        artists = artists if artists != "" else self.config.error_text
        if self.config.english_text_only:
            title = title if Utils.is_english(title) else self.config.error_text
            artists = [
                artist if Utils.is_english(artist) else self.config.error_text
                for artist in artists
            ]
        artists_str = ",".join(artists)
        return f"{title} - {artists_str}"

    @property
    def icon(self) -> str:
        """Uses polybar `Format tags -> Action` to create a clickable icon command.

        The returned string will be colored according to the Config.
        """

        program = self.player_name.split(".")[0]
        if len(program) < 2 or program is None:
            raise ValueError(f"Player: {self.player_name} cannot be handled!")
        return Utils.colorize_string(
            self.config.player_icons.get(program, self.config.player_icons["default"]),
            self.config.color,
        )

    @property
    def command_play(self) -> str:
        """A play icon with action to tell the player to play."""

        return Utils.colorize_string(
            Utils.actionize_string(
                self.config.control_icons["play"],
                f"playerctl -p {self.player_name} play",
            ),
            self.config.color,
        )

    @property
    def command_pause(self) -> str:
        """A pause icon with action to tell the player to pause."""

        return Utils.colorize_string(
            Utils.actionize_string(
                self.config.control_icons["pause"],
                f"playerctl -p {self.player_name} pause",
            ),
            self.config.color,
        )

    @property
    def command_next(self) -> str:
        """A pause icon with action to tell the player to pause."""

        return Utils.colorize_string(
            Utils.actionize_string(
                self.config.control_icons["next"],
                f"playerctl -p {self.player_name} next",
            ),
            self.config.color,
        )

    @property
    def command_previous(self) -> str:
        """A pause icon with action to tell the player to pause."""

        return Utils.colorize_string(
            Utils.actionize_string(
                self.config.control_icons["previous"],
                f"playerctl -p {self.player_name} previous",
            ),
            self.config.color,
        )

    @classmethod
    def get_available_players(cls) -> list[str]:
        """Gets list of all available players.

        If there are no players available, returns an empty list.
        """

        players_bytes = subprocess.check_output(
            ["playerctl", "-l"], stderr=subprocess.DEVNULL
        )
        if "No players found" in str(players_bytes) or len(str(players_bytes)) <= 3:
            return []
        players_list = players_bytes.decode("utf-8").rstrip().split("\n")
        return players_list


class PolyPlay:
    """PolayPlay module.

    Handles:
        - Texts displayed in the module.
        - Available players.
        - Media controls.
        - Swapping beteen available players (if applicable). Swap by clicking
            on the player icon.

    Displayed text will be of the format:
        <icon> <media_text eg: track_title - artist> | <media_controls>

    Signals are used to recieve user actions on the module i.e. clicks and scrolling.
        Currently only SIGUSR1 and SIGUSR2 are used to handle cycling players.
    """

    def __init__(self) -> None:
        self.config = Config()
        # Will be updated in the main loop
        self.player_list: list[Player] = []
        self.display_index = 0
        self.pid = os.getpid()

    @property
    def default_text(self) -> str:
        """Default text to show on the polybar module when there are no players.

        All the controls won't do anything.
        """

        icon = Utils.colorize_string(
            self.config.player_icons["default"], self.config.color
        )
        icon = Utils.actionize_string(icon, f"kill -10 {self.pid}")
        text = Utils.center_text(
            self.config.default_text, self.config.scrolling_msg_len
        )
        sep = Utils.colorize_string("|", self.config.color)
        prev = Utils.colorize_string(
            self.config.control_icons["previous"], self.config.color
        )
        play = Utils.colorize_string(
            self.config.control_icons["play"], self.config.color
        )
        next = Utils.colorize_string(
            self.config.control_icons["next"], self.config.color
        )
        return f"{icon}{text}{sep}{prev}{play}{next}"

    def _update_scrolling_text(self, player: Player) -> str:
        """Simulates the scrolling motion.

        Does so by removing the first character of the string every iteration, and
            padding the rest of the space with the start of the string.

        The scrolling text will be saved into each individual players, this way
            you retain the last displayed text when cycling between players.
        """

        # Stop the scrolling motion if the player is paused
        if not player.is_playing:
            # In the case where you startup this module and there are
            # already existing players but they are paused.
            if player.display_text == "":
                player.display_text = Utils.center_text(
                    player.metadata, self.config.scrolling_msg_len
                )
            return player.display_text

        # Construct the text to display
        scrolling_text = ""
        full_media_text = player.metadata
        # For the scrolling motion, we don't want the start of the text string immediately
        # following the end of the previous text string. We will leave a 3 spaces space.
        spacing = " " * 2
        full_media_text += spacing
        trunc_start = player.display_text_start_index
        trunc_end = trunc_start + self.config.scrolling_msg_len
        # Even if trunc_end if larger then len(full_media_text) it is fine.
        scrolling_text = full_media_text[trunc_start:trunc_end]
        # If the shortened_text no longer fills the display len, pad it with itself
        padding_text = ""
        padding_needed = len(scrolling_text) < self.config.scrolling_msg_len
        if padding_needed:
            padding_text = full_media_text[
                : (player.display_text_start_index + self.config.scrolling_msg_len)
                % len(full_media_text)
            ]
        scrolling_text += padding_text
        player.display_text_start_index = (player.display_text_start_index + 1) % len(
            full_media_text
        )
        player.display_text = scrolling_text
        return scrolling_text

    def _update_player_list(self) -> None:
        """Add new players if any, remove players if they no longer exist or is stopped."""

        new_list = Player.get_available_players()
        # Need to update the player_list
        if len(new_list) != len(self.player_list):
            for existing_player in self.player_list:
                # Remove the player from existing_player if it no longer exists
                if existing_player.player_name not in new_list:
                    self.player_list.remove(existing_player)
                # Remove the player from new list if the existing player still exists
                if existing_player.player_name in new_list:
                    new_list.remove(existing_player.player_name)
            # Now, all players left in new list (if any) are to be added to players_list
            if len(new_list) > 0:
                for player in new_list:
                    new_player = Player(player, self.config)
                    if new_player.is_stopped:
                        continue
                    self.player_list.append(new_player)

    def _select_player_to_display(self) -> Player | None:
        """Find a appropriate player to be marked as the active player.

        Uses the following rules to determine the active player:
        - Prioritize the player that is marked as active.
        - No players playing, last playing player doesn't exist, prioritize first
            player that still exist.
        - No players at all, return None.

        Note:
            Deciding against auto switching player to the active one. Leaving that
            choice with the user to manually switch between players.
        """

        if len(self.player_list) < 1:
            self.display_index = 0
            return None

        if len(self.player_list) == 1:
            self.display_index = 0
            return self.player_list[self.display_index]

        if self.display_index >= len(self.player_list) - 1:
            self.display_index = self.display_index % len(self.player_list)

        if self.display_index < 0:
            self.display_index = len(self.player_list) - 1

        return self.player_list[self.display_index]

    def cycle_player(self, sig, frame) -> None: # type: ignore
        """A callback function for handling SIGUSR1.

        It will change the active player displayed on the polybar.
        """
        if len(self.player_list) <= 1:
            self.display_index = 0
            return

        self.display_index += 1

    def reverse_cycle_player(self, sig, frame) -> None: # type: ignore
        """A callback function for handling SIGUSR2.

        It will change the active player displayed on the polybar.
        """
        if len(self.player_list) <= 1:
            self.display_index = 0
            return

        self.display_index -= 1

    def update(self) -> None:
        """Main program loop."""

        while True:
            self._update_player_list()
            active_player = self._select_player_to_display()
            if active_player:
                self._update_scrolling_text(active_player)
                icon = active_player.icon
                text = active_player.display_text
                text = Utils.actionize_string(
                    Utils.actionize_string(
                        text, f"kill -{signal.SIGUSR1.value} {self.pid}", "scroll down"
                    ),
                    f"kill -{signal.SIGUSR2.value} {self.pid}",
                    "scroll up",
                )
                sep = Utils.colorize_string("|", self.config.color)
                prev = active_player.command_previous
                play_pause = (
                    active_player.command_play
                    if not active_player.is_playing
                    else active_player.command_pause
                )
                next = active_player.command_next
                pass
                print(
                    f"{icon}{text}{sep}{prev}{play_pause}{next}",
                    flush=True,
                )
            else:
                pass
                print(self.default_text, flush=True)

            time.sleep(self.config.update_interval)


if __name__ == "__main__":
    polyplay = PolyPlay()
    signal.signal(signal.SIGUSR1, polyplay.cycle_player)
    signal.signal(signal.SIGUSR2, polyplay.reverse_cycle_player)
    polyplay.update()
