package com.carprice.backend.favorites;

import java.time.Instant;
import java.util.List;
import java.util.Map;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.carprice.backend.service.JwtService;

import lombok.RequiredArgsConstructor;


@RestController
@RequestMapping("/favorites")
@RequiredArgsConstructor
public class FavoritePredictionsController {

    private final FavoritePredictionsService favoritePredictionsService;
    private final JwtService jwtService;

    private String extractToken(String authHeader) {
        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            return authHeader.substring(7).trim();
        }
        throw new RuntimeException("Missing or invalid Authorization header");
    }

    @PostMapping("/add")
    public ResponseEntity<?> createFavorite(
        @RequestBody Map<String, Object> requestData,
        @RequestHeader("Authorization") String authHeader) {

        try {
            String jwt = extractToken(authHeader);
            String userEmail = jwtService.extractEmail(jwt);

            FavoritePredictions favorite = new FavoritePredictions();
            favorite.setBrand((String) requestData.get("brand"));
            favorite.setModel((String) requestData.get("model"));
            favorite.setMileage(((Number) requestData.get("mileage")).doubleValue());
            favorite.setEngine(((Number) requestData.get("engine")).doubleValue());
            favorite.setModelYear(((Number) requestData.get("modelYear")).intValue());
            favorite.setFuelType((String) requestData.get("fuelType"));
            favorite.setTransmission((String) requestData.get("transmission"));
            favorite.setCleanTitle((Boolean) requestData.get("cleanTitle"));
            favorite.setHasAccident((Boolean) requestData.get("hasAccident"));
            favorite.setPredictedPrice(((Number) requestData.get("predictedPrice")).doubleValue());

            System.out.println("Processed favorite object: " + favorite);

            FavoritePredictions saved = favoritePredictionsService.createFavorite(
                    userEmail,
                    favorite.getBrand(),
                    favorite.getModel(),
                    favorite.getMileage(),
                    favorite.getEngine(),
                    favorite.getModelYear(),
                    favorite.getFuelType(),
                    favorite.getTransmission(),
                    favorite.getCleanTitle(),
                    favorite.getHasAccident(),
                    favorite.getPredictedPrice(),
                    Instant.now()
            );

            return ResponseEntity.ok(saved);
        } catch (Exception e) {
            System.err.println("Error processing request:");
            e.printStackTrace();
            return ResponseEntity.badRequest().body(Map.of(
                    "error", "Bad Request",
                    "message", e.getMessage(),
                    "details", e.toString()
            ));
        }
    }

    @GetMapping
    public ResponseEntity<List<FavoritePredictions>> getAllFavorites(
            @RequestHeader("Authorization") String authHeader) {

        String jwt = extractToken(authHeader);
        String userEmail = jwtService.extractEmail(jwt);
        List<FavoritePredictions> favorites = favoritePredictionsService.getAllUserFavorites(userEmail);
        return ResponseEntity.ok(favorites);
    }

    @GetMapping("/{id}")
    public ResponseEntity<FavoritePredictions> getFavoriteById(
            @PathVariable Long id,
            @RequestHeader("Authorization") String authHeader) {

        String jwt = extractToken(authHeader);
        String userEmail = jwtService.extractEmail(jwt);
        FavoritePredictions favorite = favoritePredictionsService.getUserFavoriteById(userEmail, id);
        return ResponseEntity.ok(favorite);
    }

    @PutMapping("/{id}")
    public ResponseEntity<FavoritePredictions> updateFavorite(
            @PathVariable Long id,
            @RequestBody FavoritePredictions favoritePrediction,
            @RequestHeader("Authorization") String authHeader) {

        String jwt = extractToken(authHeader);
        String userEmail = jwtService.extractEmail(jwt);
        FavoritePredictions updatedFavorite = favoritePredictionsService.updateUserFavorite(userEmail, id, favoritePrediction);
        return ResponseEntity.ok(updatedFavorite);
    }

    @DeleteMapping("/delete/{id}")
    public ResponseEntity<Void> deleteFavorite(
            @PathVariable Long id,
            @RequestHeader("Authorization") String authHeader) {

        String jwt = extractToken(authHeader);
        String userEmail = jwtService.extractEmail(jwt);
        favoritePredictionsService.deleteUserFavorite(userEmail, id);
        return ResponseEntity.noContent().build();
    }
}