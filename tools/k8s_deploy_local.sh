#!/bin/zsh
set -e
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deploy-stable.yaml
kubectl apply -f k8s/deploy-canary.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
echo "✅ Applied. Use: kubectl -n aimoney get pods,svc,ingress"
