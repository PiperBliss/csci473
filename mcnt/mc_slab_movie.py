#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import argparse
from matplotlib.patches import Rectangle
import random
import math

class Particle:
    def __init__(self, x, y, direction, color='cyan'):
        self.x = x
        self.y = y
        self.direction = direction  # angle in radians
        self.color = color
        self.path = [(x, y)]
        self.active = True
        self.outcome = None

def simulate_step(particle, C, c, H, step_size=0.1):
    """Simulate one step of particle movement"""
    if not particle.active:
        return False

    # Move particle
    dx = step_size * math.cos(particle.direction)
    dy = step_size * math.sin(particle.direction)
    new_x = particle.x + dx
    new_y = particle.y + dy

    # Check for interaction
    interaction_prob = 1 - math.exp(-C * step_size)
    
    # Record path
    particle.path.append((new_x, new_y))
    
    # Update position
    particle.x = new_x
    particle.y = new_y

    # Check boundaries
    if new_x < 0:  # Reflected
        particle.active = False
        particle.outcome = 'Reflected'
        return False
    elif new_x > H:  # Transmitted
        particle.active = False
        particle.outcome = 'Transmitted'
        return False

    # Check for interaction
    if random.random() < interaction_prob:
        # 'c' is the scattering ratio (Sigma_s / Sigma_t)
        # 'C' is Sigma_t
        # Prob of absorption is (1 - c)
        if random.random() < (1 - c):  # Absorption # <--- FIXED (Physics Bug 1)
            particle.active = False
            particle.outcome = 'Absorbed'
            return False
        else:  # Scattering
            # Isotropic 2D scattering (0 to 2*pi)
            particle.direction = random.uniform(0, 2 * math.pi) # <--- FIXED (Physics Bug 2)

    return True

class ParticleAnimation:
    # <<< MODIFIED __init__ with particle-per-frame logic >>>
    def __init__(self, H, Sigma_t, c, N, frames, fps=30, 
                 left_margin=0.5, right_margin=0.5,
                 glow_growth=0.01, glow_size_min=0.1, glow_size_max=0.5,
                 glow_alpha_min=0.1, fig_width=10, fig_height=5,
                hud_width_ratio=0.25):

        
        self.H = H
        self.Sigma_t = Sigma_t
        self.c = c
        self.N = N
        self.frames = frames
        self.fps = fps

        hud_width_ratio = max(hud_width_ratio, 0.35)
        
        # <<< CHANGED: Calculate particles to add per frame >>>
        if self.frames > 0:
            # Use math.ceil to ensure we get all N particles
            self.particles_per_frame = math.ceil(self.N / self.frames)
        else:
            self.particles_per_frame = self.N # Add all at once if frames=0
        
        # Setup figure
        self.fig = plt.figure(figsize=(fig_width, fig_height))
        
        # Create main plot and info panel (Info on left)
        gs = self.fig.add_gridspec(1, 2, width_ratios=[hud_width_ratio, 1-hud_width_ratio])
        self.info_ax = self.fig.add_subplot(gs[0]) 
        self.ax = self.fig.add_subplot(gs[1])      
        
        # Initialize particles
        self.particles = []
        self.active_particles = 0
        self.stats = {'Reflected': 0, 'Absorbed': 0, 'Transmitted': 0}
        
        # <<< POINT 1: Added list for red dots >>>
        self.absorbed_dots = []
        
        # Setup plot
        self.setup_plot()
        
        # Animation properties
        self.glow_growth = glow_growth
        self.glow_size = glow_size_min
        self.glow_size_min = glow_size_min
        self.glow_size_max = glow_size_max
        self.glow_alpha_min = glow_alpha_min

    # <<< MODIFIED setup_plot for POINT 2 >>>
    def setup_plot(self):
        # Main plot setup
        self.ax.set_xlim(-0.5, self.H + 0.5)
        self.ax.set_ylim(-0.75, 0.75)
        self.ax.set_xlabel('x')
        self.ax.set_ylabel('y')
        self.ax.set_title(f'Neutron Slab: H={self.H}, Σt={self.Sigma_t}, c={self.c}')
        
        # <<< POINT 2: Set plot background to white >>>
        self.ax.set_facecolor('white') 

        # <<< POINT 2: Draw slab as a black rectangle >>>
        y0, y1 = self.ax.get_ylim()
        slab_height = y1 - y0
        self.ax.add_patch(Rectangle((0, y0), self.H, slab_height, color='black', zorder=0))
        
        # Set boundary lines to black
        self.ax.axvline(x=0, color='black', linestyle='-', linewidth=1)
        self.ax.axvline(x=self.H, color='black', linestyle='-', linewidth=1)
        
        # Add "Beam" label (black text)
        self.ax.text(-0.05, 0.4, 'Beam', color='black', ha='right', va='center', fontsize=9)
        
        # Set all labels and ticks to black
        self.ax.tick_params(axis='x', colors='black')
        self.ax.tick_params(axis='y', colors='black')
        self.ax.xaxis.label.set_color('black')
        self.ax.yaxis.label.set_color('black')
        self.ax.title.set_color('black')

        # Info panel setup
        self.info_ax.clear()
        self.info_ax.axis('off')
        self.update_info_panel()

    # <<< KEPT your new info_panel for POINT 5 >>>
    def update_info_panel(self):
        completed = sum(self.stats.values())
        # Ensure remaining is never negative
        remaining = max(0, self.N - completed)
        
        # Handle division by zero if N=0
        percent_completed = (completed / self.N * 100) if self.N > 0 else 0
        
        # We'll render a three-column layout: label (left), count (mid-right), percent (right)
        left_x = 0.03
        mid_x = 0.70
        right_x = 0.97
        y = 0.94
        # Increase vertical spacing for readability
        line_h = 0.075

        self.info_ax.clear()
        self.info_ax.axis('off')
        # Set figure background to white (for the info panel)
        self.fig.patch.set_facecolor('white')

        # Title
        self.info_ax.text(left_x, y, 'Outcomes', va='top', ha='left', fontfamily='monospace', fontsize=11, color='black')
        y -= line_h * 1.1

        # Header row (separate headings for count and percent)
        self.info_ax.text(left_x, y, 'Type', va='top', ha='left', fontfamily='monospace', fontsize=9, color='black')
        self.info_ax.text(mid_x, y, 'Count', va='top', ha='right', fontfamily='monospace', fontsize=9, color='black')
        self.info_ax.text(right_x, y, 'Percent', va='top', ha='right', fontfamily='monospace', fontsize=9, color='black')
        y -= line_h

        # Rows for each outcome, count and percent in separate columns
        for outcome, count in self.stats.items():
            percent = (count / self.N * 100) if self.N > 0 else 0
            # Label
            self.info_ax.text(left_x, y, outcome, va='top', ha='left', fontfamily='monospace', fontsize=9, color='black')
            # Count (right-aligned at mid column)
            self.info_ax.text(mid_x, y, f"{count:>6d}", va='top', ha='right', fontfamily='monospace', fontsize=9, color='black')
            # Percent (right-aligned at right column) - add extra spacing for readability
            self.info_ax.text(right_x, y, f"{percent:8.2f}%", va='top', ha='right', fontfamily='monospace', fontsize=9, color='black')
            y -= line_h

        # Completed and Remaining
        y -= line_h * 0.2
        self.info_ax.text(left_x, y, 'Completed', va='top', ha='left', fontfamily='monospace', fontsize=9, color='black')
        self.info_ax.text(mid_x, y, f"{completed:>6d}", va='top', ha='right', fontfamily='monospace', fontsize=9, color='black')
        self.info_ax.text(right_x, y, f"{percent_completed:8.2f}%", va='top', ha='right', fontfamily='monospace', fontsize=9, color='black')
        y -= line_h
        self.info_ax.text(left_x, y, 'Remaining', va='top', ha='left', fontfamily='monospace', fontsize=9, color='black')
        self.info_ax.text(mid_x, y, f"{remaining:>6d}", va='top', ha='right', fontfamily='monospace', fontsize=9, color='black')

    # <<< MODIFIED animate for POINTS 1, 3, 4 >>>
    def animate(self, frame):
        
        # Add the calculated number of particles per frame
        for _ in range(self.particles_per_frame):
            if len(self.particles) < self.N:
                # Start particle just at the boundary
                particle = Particle(0.001, 0, random.uniform(-math.pi/3, math.pi/3))
                self.particles.append(particle)
                self.active_particles += 1

        # Update particle positions
        self.ax.clear()
        self.setup_plot()

        # Simulate active particles
        for particle in self.particles:
            if particle.active:
                if not simulate_step(particle, self.Sigma_t, self.c, self.H):
                    self.active_particles -= 1
                    if particle.outcome:
                        self.stats[particle.outcome] = self.stats.get(particle.outcome, 0) + 1
                        
                        # <<< POINT 1: Add red dot on absorption >>>
                        if particle.outcome == 'Absorbed':
                            self.absorbed_dots.append({'x': particle.x, 'y': particle.y, 'ttl': 3})


            # <<< POINT 3 & 4: Draw path segments by location >>>
            path = np.array(particle.path)
            if len(path) > 1:
                for i in range(len(path) - 1):
                    x0, y0 = path[i]
                    x1, y1 = path[i + 1]
                    mx = 0.5 * (x0 + x1)
                    # segment color: blue if inside slab (0..H), green if outside
                    seg_color = 'blue' if (0 <= mx <= self.H) else 'green'
                    self.ax.plot([x0, x1], [y0, y1], color=seg_color, alpha=0.8, linewidth=0.9)


        # Update info panel
        self.update_info_panel()
        
        # <<< POINT 1: Draw and age red dots >>>
        if len(self.absorbed_dots) > 0:
            remaining_dots = []
            xs = []
            ys = []
            for d in self.absorbed_dots:
                xs.append(d['x'])
                ys.append(d['y'])
                d['ttl'] -= 1
                if d['ttl'] > 0:
                    remaining_dots.append(d)
            # draw scatter for current dots
            if xs:
                self.ax.scatter(xs, ys, c='red', s=20, zorder=5)
            self.absorbed_dots = remaining_dots
        
        return self.ax,

def main():
    parser = argparse.ArgumentParser(description='Create animation of neutron transport in a slab.')
    parser.add_argument('--thickness', type=float, required=True, help='Slab thickness (H)')
    parser.add_argument('--Sigma_t', type=float, required=True, help='Total cross section')
    parser.add_argument('--c', type=float, required=True, help='Ratio c=Σs/Σt')
    parser.add_argument('--N', type=int, required=True, help='Number of particles')
    parser.add_argument('--frames', type=int, required=True, help='Number of frames')
    parser.add_argument('--fps', type=int, default=30, help='Frames per second')
    parser.add_argument('--seed', type=int, help='Random seed')
    parser.add_argument('--left-margin', type=float, default=0.5)
    parser.add_argument('--right-margin', type=float, default=0.5)
    parser.add_argument('--out', default='movie.mp4', help='Output filename')
    parser.add_argument('--fade-per-frame', type=float, default=0.1)
    parser.add_argument('--glow-growth', type=float, default=0.01)
    parser.add_argument('--glow-size-min', type=float, default=0.1)
    parser.add_argument('--glow-size-max', type=float, default=0.5)
    parser.add_argument('--glow-alpha-min', type=float, default=0.1)
    parser.add_argument('--dpi', type=int, default=150)
    parser.add_argument('--fig-width', type=float, default=10)
    parser.add_argument('--fig-height', type=float, default=5)
    parser.add_argument('--hud-width-ratio', type=float, default=0.25)
    # This is the argument you had in your uploaded file
    parser.add_argument('--force-outcomes', nargs=3, type=int, metavar=('REF','ABS','TRN'),
                        help='Force final outcomes counts: reflected absorbed transmitted (three ints)')

    args = parser.parse_args()

    # Seed RNGs for reproducibility
    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)

    # Create animation object
    anim = ParticleAnimation(
        H=args.thickness,
        Sigma_t=args.Sigma_t,
        c=args.c,
        N=args.N,
        frames=args.frames,
        fps=args.fps,
        left_margin=args.left_margin,
        right_margin=args.right_margin,
        glow_growth=args.glow_growth,
        glow_size_min=args.glow_size_min,
        glow_size_max=args.glow_size_max,
        glow_alpha_min=args.glow_alpha_min,
        fig_width=args.fig_width,
        fig_height=args.fig_height,
        hud_width_ratio=args.hud_width_ratio
    )

    # Create the animation
    ani = animation.FuncAnimation(anim.fig, anim.animate,
                                  frames=args.frames,
                                  interval=1000.0/args.fps,
                                  blit=False)

    # If force-outcomes provided, set the stats
    if args.force_outcomes is not None:
        ref, absb, trn = args.force_outcomes
        anim.stats = {'Reflected': int(ref), 'Absorbed': int(absb), 'Transmitted': int(trn)}
        anim.update_info_panel() # Update panel to reflect forced counts

    # Save animation using a more robust strategy: try multiple ffmpeg codecs
    def _try_save_with_codecs(animation_obj, outpath, dpi, fps, fig):
        codec_attempts = [
            ('libx264', ['-pix_fmt', 'yuv420p']),
            ('mpeg4', ['-pix_fmt', 'yuv420p']),
            (None, None),  # let matplotlib/ffmpeg defaults run
        ]

        last_exc = None
        for codec, extra_args in codec_attempts:
            try:
                if codec is not None:
                    writer = animation.FFMpegWriter(fps=fps, codec=codec, extra_args=extra_args)
                    animation_obj.save(outpath, writer=writer, dpi=dpi,
                                       savefig_kwargs={'facecolor': fig.get_facecolor()})
                else:
                    # Let matplotlib choose the writer (typically ffmpeg)
                    animation_obj.save(outpath, fps=fps, dpi=dpi, writer='ffmpeg',
                                       savefig_kwargs={'facecolor': fig.get_facecolor()})
                return True
            except Exception as exc:
                print(f"Save attempt with codec={codec} failed: {exc}")
                last_exc = exc

        # If all ffmpeg attempts failed, try a GIF fallback (Pillow)
        try:
            from matplotlib.animation import PillowWriter
            gif_out = outpath.rsplit('.', 1)[0] + '.gif'
            pw = PillowWriter(fps=fps)
            animation_obj.save(gif_out, writer=pw, dpi=dpi)
            print(f"[ok] Saved GIF fallback: {gif_out}")
            return True
        except Exception as exc_gif:
            print(f"GIF fallback failed: {exc_gif}")
            if last_exc is not None:
                print(f"Final error (last ffmpeg attempt): {last_exc}")
            return False

    saved = _try_save_with_codecs(ani, args.out, args.dpi, args.fps, anim.fig)
    if saved:
        print(f"[ok] Saved: {args.out}")
    else:
        print("[error] Failed to save animation with ffmpeg and GIF fallback. See messages above for details.")


if __name__ == "__main__":
    main()