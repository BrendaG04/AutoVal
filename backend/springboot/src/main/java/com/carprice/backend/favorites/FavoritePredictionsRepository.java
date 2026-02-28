package com.carprice.backend.favorites;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface FavoritePredictionsRepository extends JpaRepository<FavoritePredictions, Long> {
    List<FavoritePredictions> findByUserId(UUID userId);
    boolean existsByIdAndUserId(Long id, UUID userId);

}
