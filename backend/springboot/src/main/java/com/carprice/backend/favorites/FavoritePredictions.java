package com.carprice.backend.favorites;

import com.carprice.backend.model.User;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.Instant;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "favorites")
public class FavoritePredictions {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", referencedColumnName = "id", insertable = false, updatable = false)
    private User user;

    @Column(name = "user_id", columnDefinition = "uuid")
    private UUID userId;  // Changed from Long to UUID

    private String brand;
    private String model;

    @Column(name = "model_year")
    private Integer modelYear;

    private Double mileage;
    private Double engine;

    @Column(name = "fuel_type")
    private String fuelType;

    private String transmission;

    @Column(name = "clean_title")
    @Builder.Default
    private Boolean cleanTitle = true;

    @Column(name = "has_accident", nullable = false)
    @Builder.Default
    private Boolean hasAccident = false;

    @Column(name = "predicted_price")
    private Double predictedPrice;

    @Column(name = "created_at")
    private Instant createdAt;


    @Column(columnDefinition = "jsonb")
    @JdbcTypeCode(SqlTypes.JSON)
    private String predictionData;

    @PrePersist
    protected void onCreate() {
        this.createdAt = Instant.now();
    }

}