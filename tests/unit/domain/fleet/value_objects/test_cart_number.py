"""Unit tests for CartNumber value object."""

import pytest

from app.domain.fleet.value_objects import CartNumber
from app.domain.shared.exceptions import InvalidValueException


class TestCartNumber:
    """Test suite for CartNumber value object."""
    
    def test_valid_cart_number(self):
        """Test creating valid cart numbers."""
        cart1 = CartNumber("CART001")
        assert cart1.value == "CART001"
        
        cart2 = CartNumber("AB")  # Minimum length
        assert cart2.value == "AB"
        
        cart3 = CartNumber("12345678901234567890")  # Maximum length
        assert cart3.value == "12345678901234567890"
    
    def test_normalization(self):
        """Test cart number normalization."""
        # Lowercase converted to uppercase
        cart1 = CartNumber("cart001")
        assert cart1.value == "CART001"
        
        # Spaces trimmed
        cart2 = CartNumber("  CART002  ")
        assert cart2.value == "CART002"
        
        # Mixed case normalized
        cart3 = CartNumber("CaRt003")
        assert cart3.value == "CART003"
    
    def test_empty_cart_number(self):
        """Test that empty cart number is invalid."""
        with pytest.raises(InvalidValueException) as exc:
            CartNumber("")
        assert "Cart number cannot be empty" in str(exc.value)
        
        with pytest.raises(InvalidValueException) as exc:
            CartNumber("   ")  # Only spaces
        assert "Cart number cannot be empty" in str(exc.value)
    
    def test_too_short(self):
        """Test cart number that's too short."""
        with pytest.raises(InvalidValueException) as exc:
            CartNumber("A")
        assert "Must be 2-20 alphanumeric characters" in str(exc.value)
    
    def test_too_long(self):
        """Test cart number that's too long."""
        with pytest.raises(InvalidValueException) as exc:
            CartNumber("123456789012345678901")  # 21 characters
        assert "Must be 2-20 alphanumeric characters" in str(exc.value)
    
    def test_invalid_characters(self):
        """Test cart numbers with invalid characters."""
        invalid_numbers = [
            "CART-001",  # Contains dash
            "CART_002",  # Contains underscore
            "CART 003",  # Contains space
            "CART@004",  # Contains special character
            "CART.005",  # Contains period
        ]
        
        for invalid in invalid_numbers:
            with pytest.raises(InvalidValueException) as exc:
                CartNumber(invalid)
            assert "Must be 2-20 alphanumeric characters" in str(exc.value)
    
    def test_str_conversion(self):
        """Test string conversion."""
        cart = CartNumber("CART001")
        
        assert str(cart) == "CART001"
    
    def test_equality(self):
        """Test cart number equality."""
        cart1 = CartNumber("CART001")
        cart2 = CartNumber("cart001")  # Same after normalization
        cart3 = CartNumber("CART002")
        
        assert cart1 == cart2
        assert cart1 != cart3
        assert cart1 != "CART001"  # Not equal to string
    
    def test_hash(self):
        """Test cart number hashing."""
        cart1 = CartNumber("CART001")
        cart2 = CartNumber("cart001")  # Same after normalization
        cart3 = CartNumber("CART002")
        
        assert hash(cart1) == hash(cart2)
        assert hash(cart1) != hash(cart3)
        
        # Can be used in sets
        cart_set = {cart1, cart2, cart3}
        assert len(cart_set) == 2
    
    def test_repr(self):
        """Test debug representation."""
        cart = CartNumber("CART001")
        
        assert repr(cart) == "CartNumber('CART001')"