"""
Vision API integration for chess board recognition
Supports Claude Vision, OpenAI GPT-4 Vision, and Google Gemini Vision
"""

import base64
import io
from PIL import Image, ImageEnhance
import os


class VisionAPI:
    """
    Base class for vision APIs
    """
    def __init__(self, api_key=None):
        self.api_key = api_key

    def image_to_base64(self, image):
        """
        Convert PIL Image to base64 string

        Args:
            image: PIL.Image

        Returns:
            str: Base64 encoded image
        """
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str

    def extract_fen(self, image):
        """
        Extract FEN notation from chess board image
        Must be implemented by subclass

        Args:
            image: PIL.Image of chess board

        Returns:
            str: FEN notation of the position
        """
        raise NotImplementedError


class ClaudeVision(VisionAPI):
    """
    Claude Vision API for chess board recognition
    """
    def __init__(self, api_key=None):
        super().__init__(api_key or os.getenv('ANTHROPIC_API_KEY'))
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("Install anthropic: pip install anthropic")

    def extract_fen(self, image):
        """
        Extract FEN notation using Claude Vision

        Args:
            image: PIL.Image of chess board

        Returns:
            str: FEN notation
        """
        # Convert image to base64
        img_base64 = self.image_to_base64(image)

        # Create prompt for chess board recognition
        prompt = """Analyze this chess board image and provide the position in FEN (Forsyth-Edwards Notation).

IMPORTANT: Respond with ONLY the FEN string, nothing else. No explanations, no additional text.

The FEN format is: piece_placement active_color castling en_passant halfmove fullmove

For piece placement:
- Use uppercase for white pieces (PNBRQK) and lowercase for black (pnbrqk)
- Numbers represent empty squares
- Rows are separated by /
- Start from rank 8 (top) to rank 1 (bottom)

Example FEN: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1

Respond with just the FEN string."""

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=200,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": img_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ],
                    }
                ],
            )

            # Extract FEN from response
            fen = response.content[0].text.strip()
            return fen

        except Exception as e:
            print(f"Error calling Claude Vision API: {e}")
            return None


class OpenAIVision(VisionAPI):
    """
    OpenAI GPT-4 Vision API for chess board recognition
    """
    def __init__(self, api_key=None):
        super().__init__(api_key or os.getenv('OPENAI_API_KEY'))
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("Install openai: pip install openai")

    def extract_fen(self, image):
        """
        Extract FEN notation using GPT-4 Vision

        Args:
            image: PIL.Image of chess board

        Returns:
            str: FEN notation
        """
        # Convert image to base64
        img_base64 = self.image_to_base64(image)

        prompt = """Analyze this chess board image and provide the position in FEN (Forsyth-Edwards Notation).

IMPORTANT: Respond with ONLY the FEN string, nothing else. No explanations, no additional text.

The FEN format is: piece_placement active_color castling en_passant halfmove fullmove

For piece placement:
- Use uppercase for white pieces (PNBRQK) and lowercase for black (pnbrqk)
- Numbers represent empty squares
- Rows are separated by /
- Start from rank 8 (top) to rank 1 (bottom)

Example FEN: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1

Respond with just the FEN string."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=200
            )

            # Extract FEN from response
            fen = response.choices[0].message.content.strip()
            return fen

        except Exception as e:
            print(f"Error calling OpenAI Vision API: {e}")
            return None


class GeminiVision(VisionAPI):
    """
    Google Gemini Vision API for chess board recognition
    """
    def __init__(self, api_key=None):
        super().__init__(api_key or os.getenv('GOOGLE_API_KEY'))
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            # Try latest experimental model first, fallback to stable if not available
            try:
                # Attempt gemini-2.0-flash-exp (latest)
                self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                print("Using gemini-2.0-flash-exp")
            except:
                # Fallback to gemini-1.5-pro if 2.0 not available
                self.model = genai.GenerativeModel('gemini-1.5-pro')
                print("Using gemini-1.5-pro (2.0 not available)")
        except ImportError:
            raise ImportError("Install google-generativeai: pip install google-generativeai")

    def extract_fen(self, image):
        """
        Extract FEN notation using Gemini Vision

        Args:
            image: PIL.Image of chess board

        Returns:
            str: FEN notation
        """
        prompt = """Analyze this chess board image and provide the position in FEN (Forsyth-Edwards Notation).

CRITICAL REQUIREMENTS:
1. Each rank (row) MUST have exactly 8 squares total (pieces + empty squares)
2. Count carefully - verify each rank adds up to 8
3. Respond with ONLY the FEN string - no explanations

FEN Format: piece_placement active_color castling en_passant halfmove fullmove

Piece placement rules:
- Uppercase for white pieces: P(pawn) N(knight) B(bishop) R(rook) Q(queen) K(king)
- Lowercase for black pieces: p n b r q k
- Numbers 1-8 represent consecutive empty squares
- Ranks separated by /
- Start from rank 8 (top, black's side) down to rank 1 (bottom, white's side)

VERIFICATION CHECKLIST:
- Each rank between slashes must sum to exactly 8
- Starting position: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
- Count: r(1) n(1) b(1) q(1) k(1) b(1) n(1) r(1) = 8 ✓

Common mistakes to AVOID:
- Missing pieces (e.g., "rnbqknr" has only 7 pieces - WRONG!)
- Incorrect empty square counts
- Wrong piece colors (uppercase vs lowercase)

Double-check your FEN before responding. Output ONLY the FEN string."""

        try:
            response = self.model.generate_content([prompt, image])

            # Extract FEN from response
            fen = response.text.strip()
            return fen

        except Exception as e:
            print(f"Error calling Gemini Vision API: {e}")
            return None


class BoardRecognizer:
    """
    High-level interface for board recognition
    Automatically selects available vision API
    """
    def __init__(self, prefer='gemini', preprocess=True):
        """
        Args:
            prefer: 'gemini', 'claude', or 'openai' - which API to prefer if multiple available
            preprocess: Whether to preprocess images for better recognition
        """
        self.vision_api = None
        self.preprocess = preprocess

        # Try to initialize preferred API first
        if prefer == 'gemini':
            try:
                self.vision_api = GeminiVision()
                print("Using Google Gemini Vision API for board recognition")
            except:
                pass
        elif prefer == 'claude':
            try:
                self.vision_api = ClaudeVision()
                print("Using Claude Vision API for board recognition")
            except:
                pass
        elif prefer == 'openai':
            try:
                self.vision_api = OpenAIVision()
                print("Using OpenAI Vision API for board recognition")
            except:
                pass

        # Fallback to any available API
        if self.vision_api is None:
            for api_class, api_name in [
                (GeminiVision, "Google Gemini"),
                (ClaudeVision, "Claude"),
                (OpenAIVision, "OpenAI")
            ]:
                try:
                    self.vision_api = api_class()
                    print(f"Using {api_name} Vision API for board recognition")
                    break
                except:
                    pass

        if self.vision_api is None:
            raise ValueError(
                "No vision API available. Set GOOGLE_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY"
            )

    def _preprocess_image(self, image):
        """
        Preprocess image to improve recognition accuracy

        Args:
            image: PIL.Image

        Returns:
            PIL.Image: Processed image
        """
        # Increase sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)

        # Increase contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)

        # Increase brightness slightly
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.1)

        return image

    def get_fen_from_image(self, image, num_attempts=1):
        """
        Extract FEN notation from chess board image

        Args:
            image: PIL.Image of chess board
            num_attempts: Number of attempts to make (uses most common result)

        Returns:
            str: FEN notation, or None if recognition failed
        """
        # Preprocess image if enabled
        if self.preprocess:
            image = self._preprocess_image(image)

        if num_attempts == 1:
            fen = self.vision_api.extract_fen(image)
        else:
            # Multiple attempts - use most common result
            print(f"Attempting FEN extraction {num_attempts} times...")
            results = []
            for i in range(num_attempts):
                fen_attempt = self.vision_api.extract_fen(image)
                if fen_attempt:
                    results.append(fen_attempt)
                    print(f"Attempt {i+1}: {fen_attempt}")

            if not results:
                return None

            # Find most common FEN
            from collections import Counter
            counter = Counter(results)
            fen = counter.most_common(1)[0][0]
            print(f"Using most common FEN (appeared {counter[fen]} times): {fen}")

        try:

            if not fen or len(fen) < 15:
                print(f"Invalid FEN received: {fen}")
                return None

            # Validate FEN format
            try:
                import chess
                # Try to parse the FEN - this will catch structural errors
                board = chess.Board(fen)
                return fen
            except Exception as e:
                print(f"FEN validation failed: {e}")
                print(f"Invalid FEN: {fen}")

                # Try to fix common issues
                fixed_fen = self._attempt_fen_fix(fen)
                if fixed_fen:
                    try:
                        board = chess.Board(fixed_fen)
                        print(f"Fixed FEN to: {fixed_fen}")
                        return fixed_fen
                    except:
                        pass

                return None

        except Exception as e:
            print(f"Error in board recognition: {e}")
            return None

    def _attempt_fen_fix(self, fen):
        """
        Attempt to fix common FEN errors from vision models

        Args:
            fen: Potentially invalid FEN string

        Returns:
            Fixed FEN string or None
        """
        try:
            parts = fen.split()
            if len(parts) < 1:
                return None

            position = parts[0]
            ranks = position.split('/')

            if len(ranks) != 8:
                return None

            # Check each rank has 8 squares
            fixed_ranks = []
            for rank in ranks:
                # Count pieces and empty squares
                total = 0
                for char in rank:
                    if char.isdigit():
                        total += int(char)
                    else:
                        total += 1

                # If rank is wrong length, skip fixing (too complex)
                if total != 8:
                    return None

                fixed_ranks.append(rank)

            # Rebuild FEN with default metadata if missing
            fixed_position = '/'.join(fixed_ranks)

            if len(parts) >= 6:
                # Has all parts, just use fixed position
                return f"{fixed_position} {' '.join(parts[1:])}"
            else:
                # Add default metadata: white to move, all castling rights, no en passant
                return f"{fixed_position} w KQkq - 0 1"

        except Exception as e:
            print(f"FEN fix attempt failed: {e}")
            return None


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python vision_api.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]

    # Load image
    try:
        img = Image.open(image_path)
        print(f"Loaded image: {image_path}")
    except Exception as e:
        print(f"Error loading image: {e}")
        sys.exit(1)

    # Test board recognition
    try:
        recognizer = BoardRecognizer(prefer='claude')
        print("\nExtracting FEN notation...")

        fen = recognizer.get_fen_from_image(img)

        if fen:
            print(f"\nExtracted FEN: {fen}")

            # Validate with python-chess
            try:
                import chess
                board = chess.Board(fen)
                print(f"\n✓ FEN is valid!")
                print(f"\nBoard:\n{board}")
            except Exception as e:
                print(f"\n✗ Invalid FEN: {e}")
        else:
            print("\n✗ Failed to extract FEN")

    except Exception as e:
        print(f"Error: {e}")
