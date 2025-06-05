#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
import os
import subprocess
import threading
import time
from PIL import Image, ImageTk

class AIPictureFrame:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI Picture Frame")
        
        # Make it full screen (480x320 for our LCD)
        self.root.geometry("480x320")
        self.root.configure(bg='black')
        self.root.attributes('-fullscreen', True)
        
        # Disable cursor
        self.root.configure(cursor="none")
        
        # File paths
        self.current_image_path = "/home/pi/ai-pictures/current_image.png"
        self.onnxstream_path = "/home/pi/ai-image-gen/OnnxStream/src/build/sd"
        self.models_path = "/home/pi/ai-image-gen/stable-diffusion-xl-turbo-1.0-onnxstream"
        
        # Create pictures directory
        os.makedirs("/home/pi/ai-pictures", exist_ok=True)
        
        # State tracking
        self.is_generating = False
        self.current_mode = "picture"  # "picture" or "generate"
        self.last_activity = time.time()
        self.screensaver_active = False
        
        # Create UI
        self.setup_ui()
        
        # Check for existing image and set initial mode
        self.check_initial_state()
        
        # Bind events
        self.setup_event_bindings()
        
        # Start activity monitoring
        self.monitor_activity()
        
        # Disable system screensaver
        self.disable_system_screensaver()
    
    def setup_focus_bindings(self):
        """Setup focus event bindings for better visual feedback"""
        # Text entry focus events
        self.prompt_entry.bind('<FocusIn>', lambda e: self.on_focus_in(self.prompt_entry))
        self.prompt_entry.bind('<FocusOut>', lambda e: self.on_focus_out(self.prompt_entry))
        
        # Generate button focus events
        self.generate_btn.bind('<FocusIn>', lambda e: self.on_focus_in(self.generate_btn))
        self.generate_btn.bind('<FocusOut>', lambda e: self.on_focus_out(self.generate_btn))
        
        # Back button focus events  
        self.back_btn.bind('<FocusIn>', lambda e: self.on_focus_in(self.back_btn))
        self.back_btn.bind('<FocusOut>', lambda e: self.on_focus_out(self.back_btn))
    
    def on_focus_in(self, widget):
        """Handle widget gaining focus"""
        if isinstance(widget, tk.Entry):
            widget.configure(highlightcolor='#2196F3', highlightbackground='#2196F3')
        elif isinstance(widget, tk.Button):
            # Make focused button more prominent
            current_bg = widget.cget('bg')
            if current_bg == '#4CAF50':  # Generate button
                widget.configure(bg='#66BB6A', relief='solid', borderwidth=3)
            elif current_bg == '#666666':  # Back button
                widget.configure(bg='#888888', relief='solid', borderwidth=3)
    
    def setup_event_bindings(self):
        """Handle widget losing focus"""
        if isinstance(widget, tk.Entry):
            widget.configure(highlightcolor='#333333', highlightbackground='#333333')
        elif isinstance(widget, tk.Button):
            # Return button to normal appearance
            current_bg = widget.cget('bg')
            if current_bg == '#66BB6A':  # Generate button
                widget.configure(bg='#4CAF50', relief='flat', borderwidth=3)
            elif current_bg == '#888888':  # Back button
                widget.configure(bg='#666666', relief='flat', borderwidth=3)
        """Setup all event bindings"""
        # Global activity tracking
        self.root.bind('<Button-1>', self.on_activity)
        self.root.bind('<Key>', self.on_activity)
        self.root.bind('<Motion>', self.on_activity)
        
        # Specific click handlers will be bound to widgets individually
        self.root.focus_set()
    
    def setup_ui(self):
        # Create main container
        self.main_frame = tk.Frame(self.root, bg='black')
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Picture frame mode widgets
        self.picture_label = tk.Label(
            self.main_frame, 
            bg='black', 
            fg='white',
            cursor='hand2'  # Show it's clickable
        )
        
        # Generation mode widgets
        self.gen_frame = tk.Frame(self.main_frame, bg='black')
        
        # Welcome text
        self.welcome_label = tk.Label(
            self.gen_frame,
            text="AI Picture Frame",
            font=('Arial', 18, 'bold'),
            bg='black',
            fg='white'
        )
        self.welcome_label.pack(pady=20)
        
        # Instruction text
        self.instruction_label = tk.Label(
            self.gen_frame,
            text="Type what you'd like to create:",
            font=('Arial', 12),
            bg='black',
            fg='white'
        )
        self.instruction_label.pack(pady=10)
        
        # Text input
        self.prompt_entry = tk.Entry(
            self.gen_frame,
            font=('Arial', 14),
            width=30,
            justify='center',
            relief='solid',
            borderwidth=2,
            highlightthickness=3,
            highlightbackground='#333333',
            highlightcolor='#2196F3'
        )
        self.prompt_entry.pack(pady=10)
        self.prompt_entry.bind('<Return>', self.on_generate)
        
        # Setup focus event bindings for better visual feedback
        self.setup_focus_bindings()
        
        # Generate button
        self.generate_btn = tk.Button(
            self.gen_frame,
            text="Generate Image!",
            font=('Arial', 14, 'bold'),
            bg='#4CAF50',
            fg='white',
            command=self.on_generate,
            width=20,
            height=2,
            relief='flat',
            borderwidth=3
        )
        self.generate_btn.pack(pady=20)
        
        # Back button (for returning to image)
        self.back_btn = tk.Button(
            self.gen_frame,
            text="← Back to Image",
            font=('Arial', 10),
            bg='#666666',
            fg='white',
            command=self.back_to_image,
            width=15,
            relief='flat',
            borderwidth=3
        )
        
        # Progress bar
        self.progress = ttk.Progressbar(
            self.gen_frame,
            mode='indeterminate',
            length=300
        )
        
        # Status label
        self.status_label = tk.Label(
            self.gen_frame,
            text="",
            font=('Arial', 10),
            bg='black',
            fg='yellow'
        )
        
        # Touch instruction for picture mode
        self.touch_label = tk.Label(
            self.main_frame,
            text="Click image to create new",
            font=('Arial', 12),
            bg='black',
            fg='gray',
            anchor='s'
        )
        
        # Screensaver overlay (hidden initially)
        self.screensaver_frame = tk.Frame(self.root, bg='black')
        self.screensaver_label = tk.Label(
            self.screensaver_frame,
            text="Touch anywhere to wake",
            font=('Arial', 14),
            bg='black',
            fg='#333333'
        )
        
    def check_initial_state(self):
        """Check if current_image.png exists and set initial mode"""
        if os.path.exists(self.current_image_path):
            self.show_picture_mode()
        else:
            self.show_generation_mode()
    
    def show_picture_mode(self):
        """Show full-screen image with click-to-create functionality"""
        self.current_mode = "picture"
        
        # Hide generation widgets
        self.gen_frame.pack_forget()
        
        # Load and display image
        try:
            # Open and resize image to fit screen
            img = Image.open(self.current_image_path)
            
            # Calculate scaling to fit 480x320 while maintaining aspect ratio
            img_width, img_height = img.size
            screen_width, screen_height = 480, 320
            
            # Calculate scale factor
            scale_w = screen_width / img_width
            scale_h = screen_height / img_height
            scale = min(scale_w, scale_h)
            
            # Resize image
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            self.photo = ImageTk.PhotoImage(img)
            
            # Update label and bind click event
            self.picture_label.configure(image=self.photo)
            self.picture_label.pack(fill=tk.BOTH, expand=True)
            
            # Bind click event to image
            self.picture_label.bind('<Button-1>', self.on_image_click)
            
            # Show touch instruction at bottom
            self.touch_label.pack(side=tk.BOTTOM, pady=5)
            
        except Exception as e:
            # If image can't be loaded, show generation mode
            print(f"Error loading image: {e}")
            self.show_generation_mode()
    
    def show_generation_mode(self):
        """Show generation interface"""
        self.current_mode = "generate"
        
        # Hide picture widgets
        self.picture_label.pack_forget()
        self.touch_label.pack_forget()
        
        # Show generation interface
        self.gen_frame.pack(fill=tk.BOTH, expand=True)
        
        # Show back button only if we have an image to go back to
        if os.path.exists(self.current_image_path):
            self.back_btn.pack(anchor='nw', padx=10, pady=5)
        else:
            self.back_btn.pack_forget()
        
        # Focus on text entry
        self.prompt_entry.focus_set()
        
        # Clear the text box
        self.prompt_entry.delete(0, tk.END)
        
        # Clear any previous status
        self.status_label.pack_forget()
        self.progress.pack_forget()
    
    def back_to_image(self):
        """Return to image viewing mode"""
        if os.path.exists(self.current_image_path):
            self.show_picture_mode()
        else:
            # No image to show, stay in generation mode
            pass
    
    def on_image_click(self, event):
        """Handle clicking on the displayed image"""
        if self.current_mode == "picture" and not self.is_generating:
            self.show_generation_mode()
    
    def on_activity(self, event=None):
        """Handle any user activity"""
        self.last_activity = time.time()
        
        # If screensaver is active, wake up to picture mode (not generation mode)
        if self.screensaver_active:
            self.wake_from_screensaver()
            return "break"  # Prevent event from propagating further
    
    def wake_from_screensaver(self):
        """Wake from screensaver - ALWAYS go to picture mode"""
        if self.screensaver_active:
            self.screensaver_active = False
            self.screensaver_frame.place_forget()
            
            # ALWAYS wake to picture mode if we have an image
            if os.path.exists(self.current_image_path):
                self.show_picture_mode()
            else:
                # No image exists, show generation mode
                self.show_generation_mode()
    
    def enter_screensaver(self):
        """Enter screensaver mode"""
        if not self.screensaver_active:
            self.screensaver_active = True
            
            # Show screensaver overlay
            self.screensaver_frame.place(x=0, y=0, relwidth=1, relheight=1)
            self.screensaver_label.place(relx=0.5, rely=0.5, anchor='center')
            
            # Bind click events to screensaver for wake-up
            self.screensaver_frame.bind('<Button-1>', self.on_activity)
            self.screensaver_label.bind('<Button-1>', self.on_activity)
    
    def monitor_activity(self):
        """Monitor for inactivity and manage screensaver"""
        current_time = time.time()
        
        # Enter screensaver after 5 minutes of inactivity
        if not self.screensaver_active and not self.is_generating:
            if (current_time - self.last_activity) > 300:  # 5 minutes
                self.enter_screensaver()
        
        # Check again in 30 seconds
        self.root.after(30000, self.monitor_activity)
    
    def disable_system_screensaver(self):
        """Disable system screensaver"""
        try:
            subprocess.run(['xset', 's', 'off'], check=False)
            subprocess.run(['xset', '-dpms'], check=False)
            subprocess.run(['xset', 's', 'noblank'], check=False)
        except:
            pass  # Don't fail if xset not available
    
    def on_generate(self, event=None):
        """Start image generation"""
        if self.is_generating:
            return
            
        prompt = self.prompt_entry.get().strip()
        if not prompt:
            self.show_status("Please enter a prompt!")
            return
        
        # Hide back button during generation
        self.back_btn.pack_forget()
        
        # Start generation in background thread
        self.is_generating = True
        self.generate_btn.configure(state='disabled', text='Generating...')
        self.progress.pack(pady=10)
        self.progress.start()
        self.show_status(f"Creating '{prompt}'... This takes about 3 minutes!")
        
        # Start generation thread
        thread = threading.Thread(target=self.generate_image, args=(prompt,))
        thread.daemon = True
        thread.start()
    
    def generate_image(self, prompt):
        """Generate image using OnnxStream"""
        try:
            # Create temporary output path
            temp_output = "/tmp/generated_image.png"
            
            # Run OnnxStream command
            cmd = [
                self.onnxstream_path,
                "--turbo",
                "--models-path", self.models_path,
                "--prompt", prompt,
                "--steps", "1",
                "--output", temp_output,
                "--rpi",
                "--not-tiled"
            ]
            
            # Run generation
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and os.path.exists(temp_output):
                # Move to current image location
                os.rename(temp_output, self.current_image_path)
                self.root.after(0, self.generation_complete, True)
            else:
                self.root.after(0, self.generation_complete, False, "Generation failed")
                
        except subprocess.TimeoutExpired:
            self.root.after(0, self.generation_complete, False, "Generation timed out")
        except Exception as e:
            self.root.after(0, self.generation_complete, False, str(e))
    
    def generation_complete(self, success, error_msg=None):
        """Handle generation completion"""
        self.is_generating = False
        self.progress.stop()
        self.progress.pack_forget()
        
        if success:
            self.show_status("Image created! Displaying...")
            # Automatically switch to picture mode after generation
            self.root.after(1000, self.show_picture_mode)
        else:
            self.show_status(f"Error: {error_msg}")
            self.generate_btn.configure(state='normal', text='Generate Image!')
            # Show back button again on error
            if os.path.exists(self.current_image_path):
                self.back_btn.pack(anchor='nw', padx=10, pady=5)
    
    def show_status(self, message):
        """Show status message"""
        self.status_label.configure(text=message)
        self.status_label.pack(pady=5)
        
        # Auto-hide status after 3 seconds (unless it's a generation message)
        if not self.is_generating:
            self.root.after(3000, lambda: self.status_label.pack_forget())
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = AIPictureFrame()
    app.run()
