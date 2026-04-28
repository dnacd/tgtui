"""
Main CLI entry point for the tgt application.
"""

import asyncio
import os
import sys
import webbrowser
from typing import Optional

import typer
from rich.console import Console

from telethon.errors import SessionPasswordNeededError

from telegram_textual_tui.core.config import (
    load_application_configuration,
    save_application_configuration,
    Config,
    TELEGRAM_SESSION_PATH,
    ensure_application_directory_exists,
)
from telegram_textual_tui.core.client import TelegramManager


application = typer.Typer(
    name="tgt",
    help="Telegram terminal client (TGT)",
    no_args_is_help=True,
)
output_console = Console()


@application.command()
def init():
    """
    Perform initial application setup by generating API credentials.
    """
    current_configuration = load_application_configuration()
    if current_configuration:
        output_console.print("[green]Configuration already exists.[/green]")
        return

    output_console.print("[yellow]No configuration found.[/yellow]")
    output_console.print("Opening my.telegram.org to get API credentials...")
    webbrowser.open("https://my.telegram.org/auth?to=apps")
    
    output_console.print("\nFollow these steps:")
    output_console.print("1. Log in with your phone number.")
    output_console.print("2. Go to 'API development tools'.")
    output_console.print("3. Create a new app (if you haven't already).")
    output_console.print("4. Copy the 'App api_id' and 'App api_hash'.\n")

    api_id_input = typer.prompt("Enter your API ID").strip()
    api_hash_input = typer.prompt("Enter your API Hash").strip()

    if not api_id_input.isdigit():
        output_console.print("[red]Error: API ID must be a number.[/red]")
        raise typer.Exit(1)

    new_configuration = Config(api_id=int(api_id_input), api_hash=api_hash_input)
    save_application_configuration(new_configuration)
    output_console.print("[green]Configuration saved successfully![/green]")


@application.command()
def login(
    phone_number: Optional[str] = typer.Option(None, "--phone", "-p", help="Phone number in international format"),
):
    """
    Authenticate the application with the Telegram servers.
    """
    ensure_application_directory_exists()
    application_config = load_application_configuration()
    if not application_config:
        output_console.print("[red]No configuration found. Run 'tgt init' first.[/red]")
        raise typer.Exit(1)

    async def execute_authentication():
        telegram_manager = TelegramManager(application_config)
        await telegram_manager.connect_to_telegram()
        
        if await telegram_manager.is_client_authorized():
            user_info = await telegram_manager.get_authenticated_user_details()
            output_console.print(f"[green]Already logged in as {user_info.first_name}[/green]")
            await telegram_manager.disconnect_from_telegram()
            return

        nonlocal phone_number
        if not phone_number:
            phone_number = typer.prompt("Enter your phone number (+79990000000)").strip()
        else:
            phone_number = phone_number.strip()

        if not phone_number:
            output_console.print("[red]Error: Phone number cannot be empty.[/red]")
            await telegram_manager.disconnect_from_telegram()
            raise typer.Exit(1)

        try:
            await telegram_manager.client.send_code_request(phone_number)
        except Exception as error:
            output_console.print(f"[red]Failed to send code: {error}[/red]")
            await telegram_manager.disconnect_from_telegram()
            raise typer.Exit(1)

        authentication_code = typer.prompt("Enter the code you received").strip()
        if not authentication_code:
            output_console.print("[red]Error: Code cannot be empty.[/red]")
            await telegram_manager.disconnect_from_telegram()
            raise typer.Exit(1)
        
        try:
            await telegram_manager.client.sign_in(phone_number, authentication_code)
        except Exception as error:
            if isinstance(error, SessionPasswordNeededError):
                two_factor_password = typer.prompt("Enter your 2FA password", hide_input=True)
                await telegram_manager.client.sign_in(password=two_factor_password)
            else:
                output_console.print(f"[red]Login failed: {error}[/red]")
                await telegram_manager.disconnect_from_telegram()
                raise typer.Exit(1)

        user_details = await telegram_manager.get_authenticated_user_details()
        output_console.print(f"[green]Successfully logged in as {user_details.first_name}![/green]")
        await telegram_manager.disconnect_from_telegram()

    asyncio.run(execute_authentication())


@application.command()
def tui():
    """
    Launch the graphical Textual TUI.
    """
    from telegram_textual_tui.tui.app import TGTApp
    application_instance = TGTApp()
    application_instance.run()


@application.command()
def session():
    """
    Display the absolute path to the current Telegram session file.
    """
    output_console.print(f"[cyan]Session path:[/cyan] {TELEGRAM_SESSION_PATH}.session")


@application.command()
def logout():
    """
    Securely log out and delete the local session file.
    """
    full_session_file_path = f"{TELEGRAM_SESSION_PATH}.session"
    if os.path.exists(full_session_file_path):
        os.remove(full_session_file_path)
        output_console.print("[green]Logged out and session removed.[/green]")
    else:
        output_console.print("[yellow]No active session found.[/yellow]")


@application.command()
def doctor():
    """
    Perform a system check and display diagnostic information.
    """
    import platform
    from telegram_textual_tui import __version__
    
    output_console.print(f"TGT Version: {__version__}")
    output_console.print(f"Python Version: {sys.version.split()[0]}")
    output_console.print(f"Platform: {platform.platform()}")
    
    current_config = load_application_configuration()
    output_console.print(f"Config exists: {'[green]Yes[/green]' if current_config else '[red]No[/red]'}")
    
    session_file_exists = os.path.exists(f"{TELEGRAM_SESSION_PATH}.session")
    output_console.print(f"Session exists: {'[green]Yes[/green]' if session_file_exists else '[red]No[/red]'}")
    
    output_console.print("Backend: [blue]None[/blue]")
    output_console.print("Telemetry: [blue]None[/blue]")


def main():
    """
    Main entry point for the Typer CLI application.
    """
    application()


if __name__ == "__main__":
    main()
