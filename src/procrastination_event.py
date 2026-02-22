import tkinter as tk



class ProcrastinationEvent:
    def show_popup(self, ai_message):
        root = tk.Tk()
        root.title("Focus Reminder")
        root.attributes('-fullscreen', True)
        root.configure(bg='white')

        label = tk.Label(
            root,
            text=ai_message,
            font=("Helvetica", 24),
            bg='white',
            fg='black',
            wraplength=root.winfo_screenwidth() - 100
        )
        label.pack(expand=True)

        root.mainloop()

    def play_countdown(self, count, brief_message="You have 10 seconds to close it."):
        root = tk.Tk()
        root.title(brief_message)

        # Make the window stay on top
        root.attributes('-topmost', True)

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        window_width = 400
        window_height = 100

        position_top = int(screen_height / 2 - window_height / 2)
        position_right = int(screen_width / 2 - window_width / 2)

        root.geometry(f'{window_width}x{window_height}+{position_right}+{position_top}')

        label = tk.Label(root, font=('Helvetica', 48), fg='red')
        label.pack(expand=True)

        def countdown(start_count):
            try:
                label['text'] = start_count
                if start_count > 0:
                    root.after(1000, countdown, start_count - 1)
                else:
                    root.destroy()
            except tk.TclError:
                pass  # Window already closed by user

        countdown(count)
        root.mainloop()


if __name__ == "__main__":
    procrastination_event = ProcrastinationEvent()
    procrastination_event.show_popup("You are procrastinating. Please focus on your work.")
    procrastination_event.play_countdown(10)
