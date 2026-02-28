package com.carprice.backend.favorites;


import com.carprice.backend.model.User;
import com.carprice.backend.model.UserRepository;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.UUID;


@Service
@RequiredArgsConstructor
public class FavoritePredictionsService {

    private final FavoritePredictionsRepository favoritePredictionsRepository;
    private final UserRepository userRepository;

    @Transactional
    public FavoritePredictions createFavorite(String userEmail,
                                              String brand,
                                              String model,
                                              Double mileage,
                                              Double engine,
                                              Integer modelYear,
                                              String fuelType,
                                              String transmission,
                                              Boolean cleanTitle,
                                              Boolean hasAccident,
                                              Double predictedPrice,
                                              Instant createdAt) {
        System.out.println("Searching for user with email: " + userEmail);

        User user = userRepository.findByEmail(userEmail)
                .orElseThrow(() -> new RuntimeException("User not found"));

        System.out.println("Found user: " + user.getId() + " - " + user.getEmail());

        FavoritePredictions favoritePrediction = new FavoritePredictions();
        favoritePrediction.setUserId(user.getId());
        favoritePrediction.setBrand(brand);
        favoritePrediction.setModel(model);
        favoritePrediction.setMileage(mileage);
        favoritePrediction.setEngine(engine);
        favoritePrediction.setModelYear(modelYear);
        favoritePrediction.setFuelType(fuelType);
        favoritePrediction.setTransmission(transmission);
        favoritePrediction.setCleanTitle(cleanTitle);
        favoritePrediction.setHasAccident(hasAccident);
        favoritePrediction.setPredictedPrice(predictedPrice);
        favoritePrediction.setCreatedAt(Instant.now());

        validateFavoritePrediction(favoritePrediction);
        System.out.println("Saving favorite with user ID: " + favoritePrediction.getUserId());
        return favoritePredictionsRepository.save(favoritePrediction);
    }

    public List<FavoritePredictions> getAllUserFavorites(String userEmail) {
        User user = userRepository.findByEmail(userEmail)
                .orElseThrow(() -> new RuntimeException("User not found"));

        return favoritePredictionsRepository.findByUserId(user.getId());
    }

    public FavoritePredictions getUserFavoriteById(String userEmail, Long favoriteId) {
        FavoritePredictions favorite = favoritePredictionsRepository.findById(favoriteId)
                .orElseThrow(() -> new RuntimeException("Favorite prediction not found"));

        validateUserOwnership(userEmail, favorite.getUserId());

        return favorite;
    }

    public FavoritePredictions updateUserFavorite(String userEmail, Long favoriteId, FavoritePredictions updates) {
        FavoritePredictions existingFavorite = getUserFavoriteById(userEmail, favoriteId);

        // Update allowed fields
        existingFavorite.setBrand(updates.getBrand());
        existingFavorite.setModel(updates.getModel());
        existingFavorite.setModelYear(updates.getModelYear());
        existingFavorite.setMileage(updates.getMileage());
        existingFavorite.setEngine(updates.getEngine());
        existingFavorite.setFuelType(updates.getFuelType());
        existingFavorite.setTransmission(updates.getTransmission());
        existingFavorite.setCleanTitle(updates.getCleanTitle());
        existingFavorite.setHasAccident(updates.getHasAccident());
        existingFavorite.setPredictedPrice(updates.getPredictedPrice());
        existingFavorite.setPredictionData(updates.getPredictionData());

        return favoritePredictionsRepository.save(existingFavorite);
    }

    @Transactional
    public void deleteUserFavorite(String userEmail, Long favoriteId) {
        FavoritePredictions favorite = getUserFavoriteById(userEmail, favoriteId);
        favoritePredictionsRepository.delete(favorite);
    }

    private void validateFavoritePrediction(FavoritePredictions favoritePrediction) {
        if (favoritePrediction.getBrand() == null || favoritePrediction.getBrand().isBlank()) {
            throw new IllegalArgumentException("Brand is required");
        }
        if (favoritePrediction.getModel() == null || favoritePrediction.getModel().isBlank()) {
            throw new IllegalArgumentException("Model is required");
        }
        if (favoritePrediction.getPredictedPrice() == null) {
            throw new IllegalArgumentException("Predicted price is required");
        }
    }

    private void validateUserOwnership(String userEmail, UUID userId) {
        User user = userRepository.findByEmail(userEmail)
                .orElseThrow(() -> new RuntimeException("User not found"));

        if (!user.getId().equals(userId)) {
            throw new IllegalArgumentException("You don't have permission to access this resource");
        }
    }


}