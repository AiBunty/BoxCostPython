"""
Box Cost Calculator Service - Core business logic for costing calculations.
Ported from TypeScript calculator logic.
"""
from typing import Dict, List, Optional
from decimal import Decimal, ROUND_HALF_UP
import math


class PaperLayer:
    """Represents a single paper layer in the board."""
    
    def __init__(self, bf: int, gsm: int, shade: str, is_flute: bool = False):
        self.bf = bf
        self.gsm = gsm
        shade = shade
        self.is_flute = is_flute


class BoxSpecification:
    """Box specifications for calculation."""
    
    def __init__(
        self,
        length: float,  # mm
        width: float,  # mm
        height: float,  # mm
        ply: int,
        quantity: int,
        paper_layers: List[PaperLayer],
        fluting_factor: float = 1.35,
        conversion_rate: float = 15.0,  # Rs per Kg
        printing_cost: float = 0.0,
        die_cost: float = 0.0
    ):
        self.length = length
        self.width = width
        self.height = height
        self.ply = ply
        self.quantity = quantity
        self.paper_layers = paper_layers
        self.fluting_factor = fluting_factor
        self.conversion_rate = conversion_rate
        self.printing_cost = printing_cost
        self.die_cost = die_cost


class CalculationResult:
    """Result of box cost calculation."""
    
    def __init__(self):
        self.sheet_length: float = 0
        self.sheet_width: float = 0
        self.sheet_area: float = 0  # sq meters
        self.paper_weight: float = 0  # kg per box
        self.board_thickness: float = 0  # mm
        self.paper_cost: float = 0
        self.manufacturing_cost: float = 0
        self.conversion_cost: float = 0
        self.unit_cost: float = 0
        self.total_cost: float = 0
        self.ect: Optional[float] = None
        self.bct: Optional[float] = None
        self.burst_strength: Optional[float] = None


class BoxCalculator:
    """
    Main calculator class for box costing.
    Implements all formulas from TypeScript version.
    """
    
    # Constants
    GLUE_FLAP = 30  # mm
    DECKLE_ALLOWANCE = 25  # mm (12.5 mm on each side)
    SHEET_ALLOWANCE = 15  # mm
    GSM_TO_KG_FACTOR = 1000000  # Convert GSM to kg/sq.m
    
    def calculate(
        self,
        spec: BoxSpecification,
        paper_rates: Dict[tuple, float],  # {(bf, gsm, shade): rate}
        business_defaults: Optional[Dict] = None
    ) -> CalculationResult:
        """
        Calculate complete box costing.
        
        Args:
            spec: Box specifications
            paper_rates: Dictionary of paper rates by (bf, gsm, shade)
            business_defaults: Optional business defaults for GST etc.
            
        Returns:
            CalculationResult: Complete calculation results
        """
        result = CalculationResult()
        
        # 1. Calculate sheet dimensions
        result.sheet_length, result.sheet_width = self._calculate_sheet_dimensions(
            spec.length, spec.width, spec.height
        )
        result.sheet_area = (result.sheet_length * result.sheet_width) / self.GSM_TO_KG_FACTOR
        
        # 2. Calculate paper weight
        result.paper_weight = self._calculate_paper_weight(
            result.sheet_area,
            spec.paper_layers,
            spec.fluting_factor
        )
        
        # 3. Calculate board thickness
        result.board_thickness = self._calculate_board_thickness(
            spec.paper_layers,
            spec.fluting_factor
        )
        
        # 4. Calculate paper cost
        result.paper_cost = self._calculate_paper_cost(
            result.paper_weight,
            spec.paper_layers,
            paper_rates
        )
        
        # 5. Calculate manufacturing costs
        result.manufacturing_cost = spec.printing_cost + spec.die_cost
        
        # 6. Calculate conversion cost (per kg)
        result.conversion_cost = result.paper_weight * spec.conversion_rate
        
        # 7. Calculate unit cost per box
        result.unit_cost = (
            result.paper_cost +
            result.manufacturing_cost +
            result.conversion_cost
        )
        
        # 8. Calculate total cost
        result.total_cost = result.unit_cost * spec.quantity
        
        # 9. Calculate strength values
        result.ect = self._calculate_ect(spec.paper_layers)
        result.bct = self._calculate_bct(
            result.ect,
            spec.length,
            spec.width,
            spec.height,
            result.board_thickness
        )
        result.burst_strength = self._calculate_burst_strength(spec.paper_layers)
        
        return result
    
    def _calculate_sheet_dimensions(
        self,
        length: float,
        width: float,
        height: float
    ) -> tuple:
        """
        Calculate sheet dimensions from box dimensions.
        Formula: Sheet = 2*(L+W) + 2*H + allowances
        """
        sheet_length = (
            2 * (length + width) +
            self.GLUE_FLAP +
            self.DECKLE_ALLOWANCE +
            self.SHEET_ALLOWANCE
        )
        
        sheet_width = (
            2 * height +
            self.DECKLE_ALLOWANCE +
            self.SHEET_ALLOWANCE
        )
        
        return sheet_length, sheet_width
    
    def _calculate_paper_weight(
        self,
        sheet_area: float,  # sq meters
        layers: List[PaperLayer],
        fluting_factor: float
    ) -> float:
        """
        Calculate total paper weight per box.
        Formula: Weight = Area * Σ(GSM * fluting_factor_if_flute) / 1000
        """
        total_gsm = 0
        
        for layer in layers:
            if layer.is_flute:
                # Flute layers use fluting factor
                total_gsm += layer.gsm * fluting_factor
            else:
                # Liner layers use actual GSM
                total_gsm += layer.gsm
        
        # Convert to kg: area (sq.m) * total_gsm / 1000
        weight_kg = sheet_area * total_gsm / 1000
        
        return round(weight_kg, 4)
    
    def _calculate_board_thickness(
        self,
        layers: List[PaperLayer],
        fluting_factor: float
    ) -> float:
        """
        Calculate total board thickness.
        Simplified: thickness ≈ Σ(GSM / 130) for liners + flute height
        """
        thickness = 0
        
        for layer in layers:
            if layer.is_flute:
                # Flute contributes more height (assume 4mm for A-flute)
                thickness += 4.0
            else:
                # Liner thickness approximation
                thickness += layer.gsm / 130
        
        return round(thickness, 3)
    
    def _calculate_paper_cost(
        self,
        weight: float,
        layers: List[PaperLayer],
        rates: Dict[tuple, float]
    ) -> float:
        """
        Calculate paper cost based on weight and rates.
        Formula: Cost = Weight * Weighted_Average_Rate
        """
        total_rate = 0
        total_gsm = 0
        
        for layer in layers:
            rate_key = (layer.bf, layer.gsm, layer.shade)
            rate = rates.get(rate_key, 0)
            
            # Weight by GSM contribution
            total_rate += rate * layer.gsm
            total_gsm += layer.gsm
        
        avg_rate = total_rate / total_gsm if total_gsm > 0 else 0
        paper_cost = weight * avg_rate
        
        return round(paper_cost, 2)
    
    def _calculate_ect(self, layers: List[PaperLayer]) -> Optional[float]:
        """
        Calculate Edge Crush Test (ECT) value.
        Simplified: ECT = Σ(RCT_values) where RCT ≈ BF * 0.1
        """
        total_rct = 0
        
        for layer in layers:
            if not layer.is_flute:
                # Only liner layers contribute to ECT
                rct = layer.bf * 0.1  # Simplified approximation
                total_rct += rct
        
        # ECT formula (simplified)
        ect = total_rct * 1.5
        
        return round(ect, 2) if ect > 0 else None
    
    def _calculate_bct(
        self,
        ect: Optional[float],
        length: float,
        width: float,
        height: float,
        thickness: float
    ) -> Optional[float]:
        """
        Calculate Box Compression Test (BCT) using McKee formula.
        Formula: BCT = 5.87 * ECT * √(thickness) * √(perimeter)
        """
        if not ect or ect <= 0:
            return None
        
        perimeter = 2 * (length + width)  # mm
        
        # McKee formula
        bct = 5.87 * ect * math.sqrt(thickness) * math.sqrt(perimeter)
        
        return round(bct, 2)
    
    def _calculate_burst_strength(self, layers: List[PaperLayer]) -> Optional[float]:
        """
        Calculate Burst Strength (BS).
        Formula: BS = Σ(BF of all layers)
        """
        total_bf = sum(layer.bf for layer in layers if not layer.is_flute)
        
        return round(total_bf, 2) if total_bf > 0 else None


class PaperPricingCalculator:
    """
    Calculator for paper pricing with BF, GSM, and shade adjustments.
    """
    
    @staticmethod
    def calculate_paper_rate(
        bf: int,
        gsm: int,
        shade: str,
        bf_base_price: float,
        gsm_rules: Dict,
        shade_premium: float = 0,
        market_adjustment: float = 0
    ) -> float:
        """
        Calculate final paper rate with all adjustments.
        
        Formula:
        Final Rate = BF Base Price + GSM Adjustment + Shade Premium + Market Adjustment
        
        Args:
            bf: Bursting Factor
            gsm: Grams per Square Meter
            shade: Paper shade
            bf_base_price: Base price for this BF
            gsm_rules: GSM adjustment rules dict
            shade_premium: Premium for this shade
            market_adjustment: Global market adjustment
            
        Returns:
            float: Final calculated rate
        """
        rate = bf_base_price
        
        # GSM Adjustment
        if gsm <= gsm_rules.get('low_gsm_threshold', 101):
            rate += gsm_rules.get('low_gsm_adjustment', 0)
        elif gsm >= gsm_rules.get('high_gsm_threshold', 201):
            rate += gsm_rules.get('high_gsm_adjustment', 0)
        
        # Shade Premium
        rate += shade_premium
        
        # Market Adjustment
        rate += market_adjustment
        
        return round(rate, 2)


# Singleton calculator instance
calculator = BoxCalculator()
pricing_calculator = PaperPricingCalculator()
