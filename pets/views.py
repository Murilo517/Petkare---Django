from rest_framework.views import APIView, Request, Response, status
from .models import Pet
from groups.models import Group
from traits.models import Trait
from .serializers import PetSerializer
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination

# Create your views here.


class PetView(APIView, PageNumberPagination):
    def get(self, req: Request) -> Response:
        pets = Pet.objects.all()
        trait_param = req.query_params.get("trait", None)
        if trait_param:
            trait_filter = Pet.objects.filter(traits__name=trait_param).all()
            pets = trait_filter
        result_page = self.paginate_queryset(pets, req)
        serializer = PetSerializer(result_page, many=True)

        return self.get_paginated_response(serializer.data)

    def post(self, req: Request) -> Response:
        serializer = PetSerializer(data=req.data)
        serializer.is_valid(raise_exception=True)
        group_data = serializer.validated_data.pop("group")
        trait_data = serializer.validated_data.pop("traits")
        new_group = Group.objects.filter(
            scientific_name__iexact=group_data["scientific_name"]
        ).first()
        if not new_group:
            new_group = Group.objects.create(**group_data)
        pet_obj = Pet.objects.create(**serializer.validated_data, group=new_group)
        for trait_obj in trait_data:
            new_trait = Trait.objects.filter(name__iexact=trait_obj["name"]).first()
            if not new_trait:
                new_trait = Trait.objects.create(**trait_obj)
            pet_obj.traits.add(new_trait)
        serializer = PetSerializer(pet_obj)

        return Response(serializer.data, status.HTTP_201_CREATED)


class PetDetailView(APIView):
    def get(self, req: Request, pet_id: int) -> Response:
        pet = get_object_or_404(Pet, id=pet_id)
        serializer = PetSerializer(instance=pet)
        return Response(serializer.data, status.HTTP_200_OK)

    def patch(self, req: Request, pet_id: int) -> Response:
        pet = get_object_or_404(Pet, id=pet_id)
        serializer = PetSerializer(data=req.data, partial=True)
        serializer.is_valid(raise_exception=True)
        group_data = serializer.validated_data.pop("group", None)
        if group_data:
            try:
                group_obj = Group.objects.get(
                    scientific_name__iexact=group_data["scientific_name"]
                )
            except Group.DoesNotExist:
                group_obj = Group.objects.create(**group_data)
            finally:
                pet.group = group_obj

        trait_data = serializer.validated_data.pop("traits", None)
        if trait_data:
            pet.traits.clear()
            for trait in trait_data:
                try:
                    trait_obj = Trait.objects.get(name__iexact=trait["name"])
                except Trait.DoesNotExist:
                    trait_obj = Trait.objects.create(**trait)
                finally:
                    pet.traits.add(trait_obj)
        for key, value in serializer.validated_data.items():
            setattr(pet, key, value)
        pet.save()
        serializer = PetSerializer(instance=pet)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, req: Request, pet_id: int) -> Response:
        pet = get_object_or_404(Pet, id=pet_id)
        pet.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
